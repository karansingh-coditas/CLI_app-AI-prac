import ast
import io
import pathlib
import sys
import typing

import pytest

from actiontrack import followup_gmail_draft as g
from actiontrack.core_models import AppError, Draft, DraftResult
from actiontrack.followup_gmail_draft import DraftGateway, DryRunGateway, FakeGateway, McpGmailGateway

SRC = pathlib.Path(g.__file__)
D = Draft("rahul@x.com", "Subj", "Body text", (1,))


class T:
    """Fake transport recording calls."""

    def __init__(self, result=(False, '{"id": "d1", "link": "http://l"}'), exc=None):
        self.result, self.exc, self.calls = result, exc, []

    def __call__(self, tool, args):
        self.calls.append((tool, args))
        if self.exc:
            raise self.exc
        return self.result


def gw(t, **kw):
    return McpGmailGateway(["x"], transport=t, env={}, **kw)


def test_success_and_args():
    t = T()
    r = gw(t).create_draft(D)
    assert r == DraftResult("d1", "http://l")
    assert t.calls == [("create_draft", {"to": "rahul@x.com", "subject": "Subj", "body": "Body text"})]


def test_no_recipient():
    t = T()
    gw(t).create_draft(Draft(None, "s", "b", ()))
    assert t.calls[0][1]["to"] == ""


@pytest.mark.parametrize("exc", [FileNotFoundError("nope"), TimeoutError(), ImportError("mcp")])
def test_unavailable(exc):
    with pytest.raises(AppError) as e:
        gw(T(exc=exc)).create_draft(D)
    assert e.value.exit_code == 1 and e.value.message.startswith("Gmail connector unavailable")


def test_no_command_configured():
    with pytest.raises(AppError) as e:
        McpGmailGateway(env={}).create_draft(D)
    assert e.value.message.startswith("Gmail connector unavailable")


def test_errors():
    with pytest.raises(AppError) as e:
        gw(T(result=(True, "401 Unauthorized"))).create_draft(D)
    assert "not authenticated" in e.value.message and e.value.exit_code == 1
    with pytest.raises(AppError) as e:
        gw(T(result=(True, "quota exceeded"))).create_draft(D)
    assert e.value.message == "Gmail draft failed: quota exceeded"
    for bad in ('{"ok": true}', "created", ""):
        with pytest.raises(AppError):
            gw(T(result=(False, bad))).create_draft(D)


def test_response_shapes():
    assert gw(T(result=(False, '{"draft": {"id": "x9"}}'))).create_draft(D).draft_id == "x9"
    assert gw(T(result=(False, "Draft created, id: abc-1"))).create_draft(D).draft_id == "abc-1"


@pytest.mark.parametrize("name", ["send_email", "gmail_send", "send_draft", "get_profile"])
def test_refuses_non_draft_tools(name):
    t = T()
    with pytest.raises(AppError):
        gw(t, tool_name=name)
    assert t.calls == []
    with pytest.raises(AppError):
        McpGmailGateway(["x"], transport=t, env={"ACTIONTRACK_GMAIL_DRAFT_TOOL": name})


def test_ac13_no_send_path():
    tree = ast.parse(SRC.read_text())
    idents = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
             {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
             {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    assert not [i for i in idents if "send" in i.lower()]
    assert "send" not in g.DRAFT_TOOL.lower() and "draft" in g.DRAFT_TOOL
    assert [n for n in typing.get_type_hints(DraftGateway.create_draft)] and \
        [m for m in vars(DraftGateway) if not m.startswith("_")] == ["create_draft"]


def test_dry_run_and_fake():
    out = io.StringIO()
    r = DryRunGateway(out).create_draft(Draft(None, "S", "B", ()))
    assert r == DraftResult("dry-run") and "Subject: S" in out.getvalue() and "To: (none)" in out.getvalue()
    assert "B" in out.getvalue()
    f = FakeGateway()
    f.create_draft(D)
    f.create_draft(Draft(None, "s2", "b", ()))
    assert [d.subject for d in f.drafts] == ["Subj", "s2"]


def test_body_logged_only_when_verbose(capsys):
    gw(T()).create_draft(D)
    assert "Body text" not in capsys.readouterr().err
    gw(T(), verbose=True).create_draft(D)
    assert "Body text" in capsys.readouterr().err


def test_import_without_mcp_library():
    src = SRC.read_text()
    top_level = [n for n in ast.parse(src).body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert not [n for n in top_level if "mcp" in ast.dump(n)]


# --- real stdio transport against a fake MCP server (skipped without the optional mcp extra)
SERVER = pathlib.Path(__file__).parent / "fake_gmail_server.py"


def stdio_gw(mode="ok", timeout=20.0):
    pytest.importorskip("mcp")
    return McpGmailGateway([sys.executable, str(SERVER), mode], env={}, timeout=timeout)


def test_stdio_roundtrip():
    r = stdio_gw().create_draft(D)
    assert r.draft_id == "r-123" and r.link.endswith("r-123")


def test_stdio_auth_error():
    with pytest.raises(AppError) as e:
        stdio_gw("auth").create_draft(D)
    assert "not authenticated" in e.value.message


def test_stdio_timeout():
    with pytest.raises(AppError) as e:
        stdio_gw("slow", timeout=3).create_draft(D)
    assert e.value.message.startswith("Gmail connector unavailable")


def test_stdio_missing_command():
    with pytest.raises(AppError) as e:
        McpGmailGateway(["definitely-not-a-real-cmd-xyz"], env={}).create_draft(D)
    assert e.value.message.startswith("Gmail connector unavailable")
