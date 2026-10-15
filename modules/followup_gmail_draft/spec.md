# followup_gmail_draft — Spec

**Family:** `followup_` · **File:** `src/actiontrack/followup_gmail_draft.py`
**Depends on:** `core_models`; MCP client library (decided in plan, spike task GD-1)

## Purpose
The **only** module that talks to Gmail. Exposes a one-method gateway for creating a **draft**. There is deliberately no way to send.

## Requirements covered
FR-F3, FR-F4 (never send), FR-F8 (connector unavailable), FR-F10 (dry run), IR-1–IR-4, NFR-5, NFR-6, NFR-9 (mockable). Acceptance: AC-13.

## Public interface

```python
class DraftGateway(Protocol):
    def create_draft(self, draft: Draft) -> DraftResult        # raises AppError(exit_code=1) on failure

class McpGmailGateway:          # real adapter over the Gmail MCP connector
    def __init__(self, server_command: Sequence[str] | None = None) # default from env ACTIONTRACK_GMAIL_MCP_CMD
    def create_draft(self, draft: Draft) -> DraftResult

class DryRunGateway:            # prints the draft, calls nothing external
    def __init__(self, out: TextIO)
    def create_draft(self, draft: Draft) -> DraftResult             # DraftResult("dry-run")

class FakeGateway:              # test double; records drafts
    drafts: list[Draft]
```

## Rules
1. **No send path.** The protocol has no `send` method. The MCP adapter calls only the connector's *create draft* tool, chosen from an **allow-list** of one tool name. Any tool name containing `send` is refused (`AppError`) even if configured by mistake.
2. `Draft.to is None` creates a draft with an empty recipient (used only with `--no-recipient`); the adapter does not invent an address.
3. **Failures → `AppError(exit_code=1)`** with a clear message, nothing partially recorded:
   - connector command missing / cannot start / times out (default 30 s) → `Gmail connector unavailable: <reason>`;
   - not authenticated / auth error response → `Gmail connector not authenticated: run its login first`;
   - any other error response → `Gmail draft failed: <message>`.
4. On success return `DraftResult(draft_id, link)` from the connector response. A response without an id → `AppError`.
5. **Privacy (NFR-6):** sends only `to`, `subject`, `body` of the one draft. Logs never contain the body unless `--verbose`.
6. `DryRunGateway` writes subject, to (or `(none)`), and body to `out`; makes no network or process calls.
7. Import of the MCP library is lazy inside `McpGmailGateway` so other commands run without it.

## Open question (Q-8)
Exact connector tool name and argument schema, and how the Python CLI reaches the MCP server (stdio server command vs. other transport). Resolve in task GD-1 before building the adapter. Everything above the gateway is unaffected by the answer.

## Out of scope
Composing text (`followup_compose`), recipient policy (`followup_runner`), sending, reading mail, attachments, labels.
