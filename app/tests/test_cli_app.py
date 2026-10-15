"""End-to-end smoke tests: main([...]) in-process against fixture notes."""
import ast
import io
import pathlib
import sys

import pytest

from actiontrack import cli_app
from actiontrack.cli_app import main
from actiontrack.core_models import AppError
from actiontrack.followup_gmail_draft import FakeGateway

ATT = "  - Priya Sharma <ps@x.com>\n  - Priya Nair <pn@x.com>\n  - Rahul Mehta <rahul@x.com>\n"


def note(d, *items):
    return f"---\ndate: {d}\nattendees:\n{ATT}---\n\nTalk.\n" + "\n".join(items) + "\n"


@pytest.fixture
def notes(tmp_path):
    d = tmp_path / "notes"
    d.mkdir()
    (d / "a.md").write_text(note("2026-10-05", "- [ ] Rahul to fix the build by 2026-10-10",
                                 "- [ ] Priya Sharma to send quote by 2026-10-30",
                                 "- [ ] Priya to review the draft", "- [ ] Update docs"), encoding="utf-8")
    (d / "b.md").write_text(note("2026-10-12", "- [ ] Rahul to share the deck by Friday",
                                 "- [ ] Rahul to fix the build by 2026-10-10",
                                 "- [ ] Priya Nair to book the room — “asap”…"), encoding="utf-8")
    (d / "bad.md").write_text("no front matter here\n- [ ] Rahul to x\n", encoding="utf-8")
    return d


class Run:
    def __init__(self, tmp_path):
        self.db = str(tmp_path / "t.db")
        self.gw = FakeGateway()

    def __call__(self, *argv, env=None, gateway=True, db=True):
        out, err = io.StringIO(), io.StringIO()
        pre = ["--db", self.db, "--today", "2026-10-15"] if db else []
        code = main([*pre, *argv], env=env if env is not None else {}, stdout=out, stderr=err,
                    gateway_factory=(lambda: self.gw) if gateway else None)
        return code, out.getvalue(), err.getvalue()


@pytest.fixture
def run(tmp_path):
    return Run(tmp_path)


@pytest.fixture
def loaded(run, notes):
    assert run("ingest", str(notes))[0] == 0
    return run


def test_ingest_and_list(run, notes):  # CA-T1/T2
    code, out, err = run("ingest", str(notes))
    assert code == 0 and "2 files read, 1 skipped" in out and "6 added" in out
    assert "bad.md" in err and "missing front matter" in err and "ambiguous owner" in err
    code, out, _ = run("list")
    assert code == 0 and out.splitlines()[0].split() == ["ID", "OWNER", "TASK", "DUE", "STATUS", "SOURCE"]
    assert "fix the build" in out and "(unassigned)" in out


def test_ingest_twice(run, notes):  # CA-T3, AC-12
    run("ingest", str(notes))
    rows = run("list")[1]
    code, out, _ = run("ingest", str(notes))
    assert code == 0 and "0 added, 0 merged (duplicates), 0 updated" in out and run("list")[1] == rows


def test_list_filters(loaded):  # CA-T4/T5
    out = loaded("list", "--status", "overdue")[1]
    assert "fix the build" in out and "send quote" not in out and "overdue" in out
    out = loaded("list", "--owner", "Rahul", "--due-before", "2026-10-25")[1].splitlines()
    assert len(out) == 3 and all("Rahul" in l for l in out[1:])  # build + deck, AND-filtered


def test_list_ambiguous_and_bad_args(loaded):  # CA-T6/T7/T8
    code, out, err = loaded("list", "--owner", "Priya")
    assert code == 2 and not out and "Priya Nair <pn@x.com>" in err and "Priya Sharma <ps@x.com>" in err
    code, _, err = loaded("list", "--status", "bogus")
    assert code == 2 and "usage:" in err
    code, _, err = loaded("list", "--due-before", "12/10/2026")
    assert code == 2 and "YYYY-MM-DD" in err
    assert loaded("list", "--owner", "Anita")[0] == 2


def test_list_empty(run):  # CA-T9
    assert run("list")[:2] == (0, "No items match\n")


def test_done_flow(loaded):  # CA-T10/11/12/13, AC-9
    code, out, _ = loaded("done", "1")
    assert code == 0 and "Marked #1 done" in out
    assert "fix the build" in loaded("list", "--status", "done")[1]
    code, out, _ = loaded("done", "1")
    assert code == 0 and "already done" in out
    code, _, err = loaded("done", "999")
    assert code == 2 and "No item with id 999" in err
    assert loaded("done", "abc")[0] == 2


def test_followup_dry_run_and_real(loaded):  # CA-T14/T15, AC-10
    code, out, _ = loaded("followup", "Rahul", "--dry-run")
    assert code == 0 and "Subject: Action items follow-up — Rahul — 2026-10-15" in out and "Overdue" in out
    assert loaded.gw.drafts == []
    code, out, _ = loaded("followup", "Rahul")
    assert code == 0 and "fake-1" in out and len(loaded.gw.drafts) == 1
    assert loaded.gw.drafts[0].to == "rahul@x.com"


def test_followup_errors(loaded):  # CA-T16/T17, AC-11
    code, _, err = loaded("followup", "Priya")
    assert code == 2 and "Priya Nair <pn@x.com>" in err and loaded.gw.drafts == []
    code, _, err = loaded("followup")
    assert code == 2 and "usage:" in err


def test_gateway_error_and_unexpected(loaded, monkeypatch):  # CA-T18/T19/T20
    class Down:
        def create_draft(self, d):
            raise AppError("Gmail connector unavailable: nope")

    code = main(["--db", loaded.db, "followup", "Rahul"], env={}, stdout=io.StringIO(),
                stderr=(e := io.StringIO()), gateway_factory=Down)
    assert code == 1 and e.getvalue() == "error: Gmail connector unavailable: nope\n"

    def boom(*a, **k):
        raise ZeroDivisionError("kaboom")

    monkeypatch.setattr(cli_app, "list_items", boom)
    code, _, err = loaded("list")
    assert code == 1 and "unexpected failure (ZeroDivisionError); re-run with --verbose" in err
    assert "Traceback" not in err
    code, _, err = loaded("list", "--verbose")
    assert code == 1 and "Traceback" in err and "kaboom" in err
    code, _, err = loaded("--verbose", "list")
    assert "Traceback" in err


def test_missing_folder(run, tmp_path):  # CA-T21
    code, _, err = run("ingest", str(tmp_path / "nope"))
    assert code == 1 and err.startswith("error:")


def test_db_and_today_precedence(tmp_path, notes):  # CA-T22/T23
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    o = io.StringIO
    assert main(["--db", a, "ingest", str(notes)], env={"ACTIONTRACK_DB": b}, stdout=o(), stderr=o()) == 0
    assert pathlib.Path(a).exists() and not pathlib.Path(b).exists()
    assert main(["ingest", str(notes)], env={"ACTIONTRACK_DB": b}, stdout=o(), stderr=o()) == 0
    assert pathlib.Path(b).exists()
    out = o()
    main(["--db", a, "--today", "2026-10-15", "list", "--status", "overdue"],
         env={"ACTIONTRACK_TODAY": "2020-01-01"}, stdout=out, stderr=o())
    assert "fix the build" in out.getvalue()
    out = o()
    main(["--db", a, "list", "--status", "overdue"], env={"ACTIONTRACK_TODAY": "2020-01-01"}, stdout=out, stderr=o())
    assert out.getvalue() == "No items match\n"
    err = o()
    assert main(["--db", a, "--today", "garbage", "list"], env={}, stdout=o(), stderr=err) == 2
    assert err.getvalue().startswith("error:")


def test_help(capsys):  # CA-T24
    for argv in ([], ["ingest"], ["list"], ["done"], ["followup"]):
        out = io.StringIO()
        assert main([*argv, "--help"], stdout=out, stderr=io.StringIO()) == 0
        assert "usage:" in out.getvalue()
    out = io.StringIO()
    main(["list", "--help"], stdout=out)
    assert "includes overdue" in " ".join(out.getvalue().split())


def test_works_without_mcp_library(loaded, monkeypatch):  # CA-T25
    monkeypatch.setitem(sys.modules, "mcp", None)
    assert loaded("list")[0] == 0 and loaded("done", "2")[0] == 0
    assert loaded("followup", "Rahul", "--dry-run")[0] == 0


def test_cp1252_stream_no_unicode_error(loaded, notes):  # CA-T26
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    code = main(["--db", loaded.db, "--today", "2026-10-15", "list"], env={}, stdout=out, stderr=io.StringIO())
    out.flush()
    assert code == 0 and b"book the room" in raw.getvalue()
    out = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    assert main(["--db", loaded.db, "followup", "Rahul", "--dry-run"], env={}, stdout=out, stderr=io.StringIO()) == 0


def test_store_closed_after_commands(tmp_path, notes):  # CA-T27
    db = tmp_path / "x.db"
    for argv in (["ingest", str(notes)], ["list"], ["done", "999"], ["list", "--owner", "Anita"]):
        main(["--db", str(db), *argv], env={}, stdout=io.StringIO(), stderr=io.StringIO())
    db.unlink()  # raises PermissionError on Windows if a connection is still open
    main(["--db", str(db), "ingest", str(tmp_path / "missing")], env={}, stdout=io.StringIO(), stderr=io.StringIO())
    db.unlink()


def test_ac13_no_send_anywhere_in_package():
    src = pathlib.Path(cli_app.__file__).parent
    for f in src.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        idents = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
                 {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
                 {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        assert not [i for i in idents if "send" in i.lower()], f.name
