"""Tests for ingest_runner and followup_runner (real leaf modules, in-memory store, fixed clock)."""
import hashlib
import time
from datetime import date, datetime

import pytest

from actiontrack import ingest_runner
from actiontrack.core_models import AppError, Item, Person
from actiontrack.core_store import Store
from actiontrack.followup_gmail_draft import DryRunGateway, FakeGateway
from actiontrack.followup_runner import run_followup
from actiontrack.ingest_runner import format_report, run_ingest

NOW = datetime(2026, 10, 15, 9, 0)
TODAY = date(2026, 10, 15)
ATT = ["Priya Sharma <ps@x.com>", "Rahul Mehta <rahul@x.com>"]


def note(d="2026-10-12", att=ATT, items=()):
    a = "\n".join(f"  - {x}" for x in att)
    return f"---\ndate: {d}\nattendees:\n{a}\n---\n\nDiscussion.\n" + "\n".join(items) + "\n"


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "notes"
    d.mkdir()
    return d


def put(folder, name, text):
    (folder / name).write_text(text, encoding="utf-8")


def ingest(folder, store):
    return run_ingest(str(folder), store, NOW)


def by_task(store):
    return {i.task: i for i in store.query()}


# ----------------------------------------------------------------- ingest
def test_ig_basic_three_notes(folder, store):  # AC-1
    put(folder, "a.md", note(items=["- [ ] Priya to send the revised quote by Friday", "- [x] Rahul to share the deck"]))
    put(folder, "b.md", note("2026-10-13", items=["- [ ] Update the onboarding doc"]))
    put(folder, "c.md", note("2026-10-14", items=["- [ ] Rahul will fix the build by 2026-10-20"]))
    r = ingest(folder, store)
    assert (r.files_read, r.items_added, len(r.files_skipped)) == (3, 4, 0)
    t = by_task(store)
    q = t["send the revised quote"]
    assert q.owner.name == "Priya Sharma" and q.due_date == date(2026, 10, 16) and q.source_file.endswith("a.md")
    assert t["share the deck"].status == "done" and t["share the deck"].done_at == NOW
    assert t["Update the onboarding doc"].owner is None and t["fix the build"].due_date == date(2026, 10, 20)
    assert (r.items_unassigned, r.items_no_due) == (1, 2)


def test_ig_duplicate_across_notes_and_order(folder, store):  # AC-2, IG-T23
    put(folder, "a.md", note("2026-10-05", items=["- [ ] Priya to send quote by 2026-10-16"]))
    put(folder, "b.md", note("2026-10-12", items=["- [ ] Priya to send quote by 2026-10-23"]))
    r = ingest(folder, store)
    (i,) = store.query()
    assert i.source_file.endswith("a.md") and [f[-4:] for f in i.also_seen_in] == ["b.md"]
    assert r.items_merged == 1 and r.items_updated == 1 and i.due_date == date(2026, 10, 23)
    assert [x.code for x in r.issues] == ["DUE_CHANGED"]

    s2 = Store(":memory:")  # reversed file order: same primary
    (folder / "a.md").rename(folder / "z.md")
    ingest(folder, s2)
    (j,) = s2.query()
    assert j.source_file.endswith("z.md") and j.source_date == date(2026, 10, 5)
    assert j.due_date == date(2026, 10, 23)
    s2.close()


def test_ig_ambiguous_and_same_name_people(folder, store):  # AC-5, IG-T6
    att = ["Priya Sharma <ps@x.com>", "Priya Nair <pn@x.com>"]
    put(folder, "a.md", note(att=att, items=["- [ ] Priya to send quote", "- [ ] Priya S. to review", "- [ ] Priya N. to review"]))
    r = ingest(folder, store)
    t = by_task(store)
    amb = t["Priya to send quote"]
    assert amb.owner is None and amb.notes == ["ambiguous owner: Priya (Priya Sharma | Priya Nair)"]
    assert (r.items_ambiguous, r.items_unassigned) == (1, 1)
    assert any(i.code == "AMBIGUOUS_OWNER" and i.line == 9 for i in r.issues)
    owners = [i.owner for i in store.query() if i.owner]
    assert len(owners) == 2 and owners[0] != owners[1]
    assert "ambiguous owner" in format_report(r)


def test_ig_malformed_files(folder, store):  # AC-6, IG-T7/8/9
    put(folder, "bad1.md", "no front matter\n- [ ] Priya to x")
    put(folder, "bad2.md", note("2026-13-45", items=["- [ ] Priya to y"]))
    (folder / "bad3.md").write_bytes(b"---\ndate: 2026-10-12\n\xff\xfe\n---\n")
    put(folder, "good.md", note(items=["- [ ] Rahul to z"]))
    r = ingest(folder, store)
    assert r.files_read == 1 and len(r.files_skipped) == 3
    assert all(i.code == "MALFORMED_NOTE" and i.message for i in r.files_skipped)
    assert [i.task for i in store.query()] == ["z"]
    out = format_report(r)
    assert "1 files read, 3 skipped" in out and "bad1.md — missing front matter" in out


def test_ig_idempotent_and_done_precedence(folder, store):  # AC-12, IG-T10/11/12
    put(folder, "a.md", note(items=["- [ ] Priya to send quote by Friday", "- [ ] Rahul to share deck"]))
    ingest(folder, store)
    first = [(i.id, i.status, i.due_date, i.also_seen_in) for i in store.query()]
    r = ingest(folder, store)
    assert (r.items_added, r.items_merged, r.items_updated) == (0, 0, 0)
    assert [(i.id, i.status, i.due_date, i.also_seen_in) for i in store.query()] == first
    store.mark_done(1, NOW)
    ingest(folder, store)
    assert store.get(1).status == "done"  # `[ ]` never reopens
    put(folder, "a.md", note(items=["- [ ] Priya to send quote by Friday", "- [x] Rahul to share deck"]))
    r = ingest(folder, store)
    assert store.get(2).status == "done" and r.items_updated == 1


def test_ig_due_date_change_reingest(folder, store):  # IG-T14
    put(folder, "a.md", note(items=["- [ ] Priya to send quote by Friday"]))
    ingest(folder, store)
    put(folder, "b.md", note("2026-10-19", items=["- [ ] Priya to send quote by Friday"]))
    r = ingest(folder, store)
    assert store.get(1).due_date == date(2026, 10, 23) and r.items_updated == 1
    assert [i.code for i in r.issues] == ["DUE_CHANGED"]


def test_ig_fatal_folder_errors(tmp_path, store):  # IG-T15/16
    for p in (tmp_path / "missing", _file(tmp_path)):
        with pytest.raises(AppError) as e:
            run_ingest(str(p), store, NOW)
        assert e.value.exit_code == 1


def _file(tmp_path):
    f = tmp_path / "f.md"
    f.write_text("x")
    return f


def test_ig_only_top_level_md_and_empty(folder, store):  # IG-T17/18
    assert ingest(folder, store).files_read == 0
    put(folder, "a.md", note(items=["- [ ] Rahul to a"]))
    put(folder, "b.txt", note(items=["- [ ] Rahul to b"]))
    put(folder, "C.MD", note(items=["- [ ] Rahul to c"]))
    (folder / "sub").mkdir()
    put(folder / "sub", "d.md", note(items=["- [ ] Rahul to d"]))
    r = ingest(folder, store)
    assert r.files_read == 2 and sorted(i.task for i in store.query()) == ["a", "c"]


def test_ig_fault_isolated_per_file(folder, store, monkeypatch):  # IG-T19
    for n in "abc":
        put(folder, f"{n}.md", note(items=[f"- [ ] Rahul to do {n}"]))
    real = ingest_runner.resolve_owner

    def boom(text, att):
        if text.endswith("do b"):
            raise RuntimeError("injected")
        return real(text, att)

    monkeypatch.setattr(ingest_runner, "resolve_owner", boom)
    r = ingest(folder, store)
    assert sorted(i.task for i in store.query()) == ["do a", "do c"]
    assert r.files_read == 2 and len(r.files_skipped) == 1 and "injected" in r.files_skipped[0].message


def test_ig_unparseable_and_repeat_in_note(folder, store):  # IG-T20/21
    put(folder, "a.md", note(items=["- [ ] by Friday", "- [ ] Rahul to dup", "- [ ] Rahul to dup"]))
    r = ingest(folder, store)
    t = by_task(store)
    assert "by Friday" in t and t["by Friday"].due_date == date(2026, 10, 16) and t["by Friday"].owner is None
    assert any(i.code == "UNPARSEABLE_ITEM" for i in r.issues)
    assert len(store.query()) == 2


def test_ig_warnings_unknown_owner_bad_date(folder, store):
    put(folder, "a.md", note(items=["- [ ] Anita to book the room", "- [ ] Rahul to fix it by 31 Feb"]))
    r = ingest(folder, store)
    assert {i.code for i in r.issues} == {"UNKNOWN_OWNER", "BAD_DUE_DATE"}
    assert by_task(store)["Anita to book the room"].owner is None
    assert by_task(store)["fix it by 31 Feb"].owner.name == "Rahul Mehta"


def test_ig_sources_untouched(folder, store):  # IG-T22
    put(folder, "a.md", note(items=["- [x] Rahul to a"]))
    h = lambda: hashlib.md5((folder / "a.md").read_bytes()).hexdigest()  # noqa: E731
    before = h()
    ingest(folder, store)
    assert h() == before


def test_ig_performance(folder, store):  # IG-T24
    for n in range(500):
        put(folder, f"n{n:03}.md", note(items=[f"- [ ] Rahul to task {n}-{k} by Friday" for k in range(10)]))
    t = time.time()
    r = ingest(folder, store)
    assert r.items_added == 5000 and time.time() - t < 10


# --------------------------------------------------------------- followup
def seed(store):
    R, PS, PN, DEV = (Person("Rahul Mehta", "rahul@x.com"), Person("Priya Sharma", "ps@x.com"),
                      Person("Priya Nair", "pn@x.com"), Person("Dev Patel"))
    rows = [(R, date(2026, 10, 10), "open", "late task"), (R, date(2026, 10, 20), "open", "later task"),
            (R, None, "done", "finished"), (PS, None, "open", "ps task"), (PN, None, "open", "pn task"),
            (DEV, None, "open", "dev task"), (None, None, "open", "nobody task")]
    for n, (o, d, s, t) in enumerate(rows):
        store.add(Item(None, o, t, t, d, s, "notes/m.md", date(2026, 10, 1), f"k{n}"))


@pytest.fixture
def seeded(store):
    seed(store)
    return store


def test_fu_success(seeded):  # AC-10, FU-T1/T12
    g = FakeGateway()
    o = run_followup("Rahul", seeded, g, TODAY)
    assert o.exit_code == 0 and len(g.drafts) == 1 and g.drafts[0].to == "rahul@x.com"
    b = g.drafts[0].body
    assert b.index("Overdue") < b.index("Open") and "late task" in b and "later task" in b and "finished" not in b
    assert "fake-1" in o.message and "#1 late task" in o.message and "(overdue)" in o.message
    assert o.message.endswith("1 unassigned open item(s) not included (no recipient)")
    assert o.included_ids == (1, 2) and o.draft_result.draft_id == "fake-1"


def test_fu_ambiguous_and_lookup_errors(seeded):  # AC-11
    g = FakeGateway()
    o = run_followup("Priya", seeded, g, TODAY)
    assert o.exit_code == 2 and not g.drafts and len(o.candidates) == 2
    assert "Priya Nair <pn@x.com>" in o.message and "Priya Sharma <ps@x.com>" in o.message
    o = run_followup("Anita", seeded, g, TODAY)
    assert (o.exit_code, o.message) == (2, "No owner matches 'Anita'")
    assert run_followup("unassigned", seeded, g, TODAY).exit_code == 2 and not g.drafts


@pytest.mark.parametrize("q", ["Priya Nair", "pn@x.com"])
def test_fu_exact_owner(seeded, q):
    g = FakeGateway()
    assert run_followup(q, seeded, g, TODAY).exit_code == 0
    assert "pn task" in g.drafts[0].body and "ps task" not in g.drafts[0].body


def test_fu_nothing_to_follow_up(store):
    g = FakeGateway()
    seed(store)
    store.mark_done(1, NOW)
    store.mark_done(2, NOW)
    o = run_followup("Rahul", store, g, TODAY)
    assert o.exit_code == 0 and o.message == "Nothing to follow up for Rahul Mehta" and not g.drafts


def test_fu_no_email(seeded):
    g = FakeGateway()
    o = run_followup("Dev", seeded, g, TODAY)
    assert o.exit_code == 1 and "--no-recipient" in o.message and not g.drafts
    o = run_followup("Dev", seeded, g, TODAY, no_recipient=True)
    assert o.exit_code == 0 and g.drafts[0].to is None


def test_fu_gateway_failure_and_rerun(seeded):
    class Down:
        def create_draft(self, d):
            raise AppError("Gmail connector unavailable: x")

    before = [i for i in seeded.query()]
    with pytest.raises(AppError):
        run_followup("Rahul", seeded, Down(), TODAY)
    assert seeded.query() == before
    g = FakeGateway()
    run_followup("Rahul", seeded, g, TODAY)
    run_followup("Rahul", seeded, g, TODAY)
    assert len(g.drafts) == 2  # FR-F9


def test_fu_done_item_excluded_and_only_create_draft_used(seeded):
    seeded.mark_done(1, NOW)

    class Spy:
        used = []

        def __getattr__(self, name):
            Spy.used.append(name)
            raise AttributeError(name)

        def create_draft(self, d):
            Spy.used.append("create_draft")
            assert "late task" not in d.body
            from actiontrack.core_models import DraftResult
            return DraftResult("s1")

    assert run_followup("Rahul", seeded, Spy(), TODAY).exit_code == 0
    assert Spy.used == ["create_draft"]


def test_fu_dry_run(seeded):
    import io
    out = io.StringIO()
    o = run_followup("Rahul", seeded, DryRunGateway(out), TODAY)
    assert o.exit_code == 0 and "Subject: Action items follow-up — Rahul" in out.getvalue()
    assert "Dry run" in o.message
