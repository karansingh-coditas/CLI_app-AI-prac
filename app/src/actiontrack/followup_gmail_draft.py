"""The only module that talks to Gmail. It can create drafts; there is no way to send."""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import Callable, Mapping, Protocol, Sequence, TextIO

from .core_models import AppError, Draft, DraftResult, RUNTIME_ERROR

DRAFT_TOOL = "create_draft"  # the single connector tool we are allowed to call
DEFAULT_TIMEOUT = 30.0

# (tool_name, arguments) -> (is_error, text). Raises OSError/TimeoutError/ImportError if unreachable.
Transport = Callable[[str, dict], "tuple[bool, str]"]


class DraftGateway(Protocol):
    def create_draft(self, draft: Draft) -> DraftResult: ...


def _check_tool(name: str) -> str:
    low = name.lower()
    if "send" in low or "draft" not in low:
        raise AppError(f"refusing connector tool {name!r}: only a create-draft tool may be used", RUNTIME_ERROR)
    return name


def _stdio_transport(cmd: Sequence[str], timeout: float) -> Transport:
    def call(tool: str, args: dict) -> tuple[bool, str]:
        import asyncio  # lazy: MCP library is optional (pip install actiontrack[gmail])

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        async def go() -> tuple[bool, str]:
            params = StdioServerParameters(command=cmd[0], args=list(cmd[1:]))
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    res = await session.call_tool(tool, args)
                    return bool(getattr(res, "is_error", getattr(res, "isError", False))), "".join(getattr(c, "text", "") or "" for c in res.content)

        return asyncio.run(asyncio.wait_for(go(), timeout))

    return call


class McpGmailGateway:
    def __init__(self, server_command: Sequence[str] | None = None, *, tool_name: str | None = None,
                 timeout: float = DEFAULT_TIMEOUT, transport: Transport | None = None,
                 verbose: bool = False, env: Mapping[str, str] | None = None):
        env = os.environ if env is None else env
        self._tool = _check_tool(tool_name or env.get("ACTIONTRACK_GMAIL_DRAFT_TOOL") or DRAFT_TOOL)
        cmd = server_command or shlex.split(env.get("ACTIONTRACK_GMAIL_MCP_CMD", ""), posix=os.name != "nt")
        self._cmd, self._timeout, self._verbose = cmd, timeout, verbose
        self._transport = transport

    def create_draft(self, draft: Draft) -> DraftResult:
        transport = self._transport
        if transport is None:
            if not self._cmd:
                raise AppError("Gmail connector unavailable: set ACTIONTRACK_GMAIL_MCP_CMD to the "
                               "connector's MCP server command", RUNTIME_ERROR)
            transport = _stdio_transport(self._cmd, self._timeout)
        args = {"to": draft.to or "", "subject": draft.subject, "body": draft.body}
        if self._verbose:
            print(f"[gmail] {self._tool}: {args}", file=sys.stderr)
        try:
            is_error, text = transport(self._tool, args)
        except Exception as e:  # missing command, timeout, missing MCP lib, server died, protocol error
            while isinstance(e, BaseExceptionGroup):
                e = e.exceptions[0]
            raise AppError(f"Gmail connector unavailable: {type(e).__name__}: {e}", RUNTIME_ERROR) from e
        if is_error:
            if re.search(r"auth|credential|login|unauthori[sz]ed|\b40[13]\b", text, re.I):
                raise AppError("Gmail connector not authenticated: run its login first", RUNTIME_ERROR)
            raise AppError(f"Gmail draft failed: {text.strip() or 'unknown error'}", RUNTIME_ERROR)
        return _parse_response(text)


def _parse_response(text: str) -> DraftResult:
    draft_id = link = None
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    if isinstance(data, dict):
        inner = data.get("draft") if isinstance(data.get("draft"), dict) else data
        draft_id = inner.get("id") or inner.get("draft_id") or inner.get("draftId") or data.get("id")
        link = data.get("link") or data.get("url") or inner.get("link")
    elif (m := re.search(r"\bid\b\W{0,3}([\w-]+)", text, re.I)):
        draft_id = m.group(1)
    if not draft_id:
        raise AppError("Gmail draft failed: connector response had no draft id", RUNTIME_ERROR)
    return DraftResult(str(draft_id), link)


class DryRunGateway:
    def __init__(self, out: TextIO):
        self._out = out

    def create_draft(self, draft: Draft) -> DraftResult:
        print(f"Subject: {draft.subject}\nTo: {draft.to or '(none)'}\n\n{draft.body}\n", file=self._out)
        return DraftResult("dry-run")


class FakeGateway:
    def __init__(self) -> None:
        self.drafts: list[Draft] = []

    def create_draft(self, draft: Draft) -> DraftResult:
        self.drafts.append(draft)
        return DraftResult(f"fake-{len(self.drafts)}")
