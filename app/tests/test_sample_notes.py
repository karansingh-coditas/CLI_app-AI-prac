"""Acceptance tests against the real sample meeting notes in tests/fixtures/notes (36 files, many traps)."""
import io
import pathlib
import shutil
from datetime import date, datetime

import pytest

from actiontrack.cli_app import main
from actiontrack.core_store import Store
from actiontrack.followup_gmail_draft import FakeGateway
from actiontrack.ingest_runner import format_report, run_ingest

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "notes"
NOW = datetime(2026, 10, 15, 9, 0)


@pytest.fixture(scope="module")
def ingested():
    s = Store(":memory:")
    report = run_ingest(str(FIXTURES), s, NOW)
    yield s, report
    s.close()


def find(store, owner, task_start):
    hits = [i for i in store.query() if i.task.startswith(task_start) and (i.owner.name if i.owner else None) == owner]
    assert len(hits) == 1, (owner, task_start, hits)
    return hits[0]


def test_files_read_and_skipped(ingested):
    _, r = ingested
    assert r.files_read == 30
    assert {pathlib.Path(i.file).name: i.message for i in r.files_skipped} == {
        "2026-09-09-notes-final-v2.md": "empty file",
        "2026-09-23-standup.md": "missing or empty attendees",
        "2026-10-03-sales-pipeline.md": "missing or invalid date",
        "scratch.md": "not valid UTF-8",
        "untitled.md": "missing front matter",
    }  # the .txt file is never read


def test_counts(ingested):
    _, r = ingested
    assert (r.items_added, r.items_merged, r.items_updated) == (90, 21, 18)
    assert (r.items_unassigned, r.items_ambiguous, r.items_no_due) == (11, 5, 20)
    out = format_report(r)
    assert "30 files read, 5 skipped" in out and "scratch.md — not valid UTF-8" in out


def test_traps_are_not_items(ingested):
    s, _ = ingested
    tasks = " | ".join(i.raw_text for i in s.query())
    assert "Owner to remediate" not in tasks            # fenced code block
    assert "hardware tokens" not in tasks               # HTML comment
    assert "Karan to refund affected customers by Friday" not in tasks   # blockquote
    assert "Book the venue" not in tasks                # .txt file
    assert "chase the vendor" not in tasks              # note without header
    assert "rebase the feature branch" not in tasks     # note without attendees


def test_non_checkbox_actions_are_reported_not_dropped(ingested):
    s, r = ingested
    msgs = [i.message for i in r.issues if i.code == "UNPARSEABLE_ITEM"]
    assert len(msgs) == 2 and any("brand kit" in m for m in msgs) and any("offsite summary" in m for m in msgs)
    assert not [i for i in s.query() if "brand kit" in i.task or "offsite summary" in i.task]


def test_bullet_styles_nesting_and_done(ingested):
    s, _ = ingested
    assert find(s, "Karan Joshi", "validate targets").due_date == date(2026, 10, 5)      # nested item
    assert find(s, "Lena Fischer", "run the customer survey").due_date == date(2026, 10, 15)  # `*` bullet
    assert find(s, "Sam Okafor", "propose the on-call rotation").due_date == date(2026, 10, 15)  # `+` bullet
    assert find(s, "Karan Joshi", "approve the Q4 cloud spend").status == "done"          # `[X]`


def test_dates_resolved_from_meeting_date(ingested):
    s, _ = ingested
    assert find(s, "Anita Desai", "share first wireframes").due_date == date(2026, 9, 3)     # Tue 09-01, "Thursday"
    assert find(s, "Priya Shah", "draft the test plan").due_date == date(2026, 9, 11)        # "end of next week"
    assert find(s, "Anita Desai", "audit colour contrast").due_date == date(2026, 9, 21)     # "@anita: ... by Mon"
    assert find(s, "Sam Okafor", "schedule cutover").due_date == date(2026, 10, 10)          # "for Saturday 10 Oct"
    assert find(s, "Rahul Verma", "start SSO spike").due_date == date(2026, 10, 13)          # "next Tuesday"
    assert find(s, "Karan Joshi", "send the final contract").due_date == date(2026, 10, 15)  # "tomorrow"
    assert find(s, "Sam Okafor", "write the postmortem").due_date == date(2026, 9, 22)       # "EOD tomorrow"
    assert find(s, "Priya Nair", "send revised quote to Acme").due_date == date(2026, 9, 11)  # "— by Friday"
    assert find(s, "Sam Okafor", "cut cloud costs").due_date == date(2026, 10, 9)


def test_same_first_name_people(ingested):
    s, _ = ingested
    owners = {p.name for p in s.owners()}
    assert {"Priya Nair", "Priya Shah", "Rahul Mehta", "Rahul Verma"} <= owners
    ambiguous = [i for i in s.query() if any(n.startswith("ambiguous owner") for n in i.notes)]
    assert len(ambiguous) == 5 and all(i.owner is None for i in ambiguous)
    assert find(s, "Priya Shah", "run the invoice rounding tests")     # "Priya S."
    assert find(s, "Priya Nair", "notify customers about the maintenance window").status == "done"  # "Priya N."


def test_unassigned_kept_never_dropped(ingested):
    s, _ = ingested
    un = {i.task for i in s.query(owner_key="unassigned")}
    assert {"Someone to update the CRM notes", "TBD to write the design-system changelog",
            "Team to decide on the launch date", "Anita & Rahul to agree on the component API"} <= un
    assert len(un) == 11


def test_duplicates_merge_done_wins_latest_due(ingested):
    s, r = ingested
    wf = find(s, "Anita Desai", "share updated wireframes")      # 09-15 and 09-22 notes
    assert wf.source_file.endswith("2026-09-15-quote-portal-weekly.md") and len(wf.also_seen_in) == 1
    assert wf.due_date == date(2026, 9, 24)                      # later due date wins
    staging = find(s, "Rahul Mehta", "set up the staging environment")
    assert staging.status == "done" and staging.due_date == date(2026, 9, 8)
    assert any(i.code == "DUE_CHANGED" and "wireframes" in i.message for i in r.issues)
    assert find(s, "Anita Desai", "finalise the welcome-email copy").status == "done"   # [ ] twice, [x] later


def test_reingest_is_idempotent(ingested):
    s, _ = ingested
    before = [(i.id, i.status, i.due_date, tuple(i.also_seen_in)) for i in s.query()]
    again = run_ingest(str(FIXTURES), s, datetime(2026, 11, 1))
    assert (again.items_added, again.items_merged, again.items_updated) == (0, 0, 0)
    assert [(i.id, i.status, i.due_date, tuple(i.also_seen_in)) for i in s.query()] == before


def test_ingest_order_does_not_matter(tmp_path, ingested):
    s, _ = ingested
    files = sorted(p for p in FIXTURES.iterdir())
    rev = tmp_path / "rev"
    rev.mkdir()
    for n, f in enumerate(reversed(files)):
        shutil.copy(f, rev / f"{n:03}-{f.name}")   # same notes, opposite processing order
    s2 = Store(":memory:")
    run_ingest(str(rev), s2, NOW)
    shape = lambda st: sorted((i.task, i.owner.key if i.owner else None, i.due_date, i.status, i.source_date,  # noqa: E731
                               len(i.also_seen_in)) for i in st.query())
    assert shape(s2) == shape(s)
    s2.close()


def test_cli_end_to_end_on_sample_notes(tmp_path):
    db, gw = str(tmp_path / "s.db"), FakeGateway()

    def run(*argv):
        out, err = io.StringIO(), io.StringIO()
        code = main(["--db", db, "--today", "2026-10-15", *argv], env={}, stdout=out, stderr=err,
                    gateway_factory=lambda: gw)
        return code, out.getvalue(), err.getvalue()

    code, out, err = run("ingest", str(FIXTURES))
    assert code == 0 and "30 files read, 5 skipped" in out and "skipped:" in err and "Traceback" not in err
    code, out, _ = run("list", "--status", "overdue")
    assert code == 0 and "fix the pagination bug" in out
    assert all(" overdue " in row for row in out.splitlines()[1:])
    assert run("list", "--owner", "Priya")[0] == 2 and run("list", "--owner", "Rahul")[0] == 2
    code, out, _ = run("list", "--owner", "Karan", "--due-before", "2026-10-02")
    assert code == 0 and "send the vendor invoice list" in out and "approve the Q4 cloud spend" not in out.split("\n", 1)[0]
    assert run("followup", "Karan")[0] == 1                       # sample notes carry no emails
    code, out, _ = run("followup", "Karan", "--no-recipient")
    assert code == 0 and gw.drafts[0].to is None and "Karan" in gw.drafts[0].subject
    assert run("list", "--owner", "unassigned")[0] == 0
