"""Tests for track_owner_lookup, track_list, track_done, followup_compose."""
import ast
import pathlib
import sys
from datetime import date, datetime

import pytest

from actiontrack.core_models import Item, Person, is_overdue
from actiontrack.core_store import Store
from actiontrack.followup_compose import compose
from actiontrack.track_done import mark_done
from actiontrack.track_list import format_table, list_items
from actiontrack.track_owner_lookup import lookup_owner

SRC = pathlib.Path(__file__).parents[1] / "src/actiontrack"
TODAY = date(2026, 10, 15)
PS, PN = Person("Priya Sharma", "ps@x.com"), Person("Priya Nair", "pn@x.com")
RM = Person("Rahul Mehta", "rahul@x.com")

# ----------------------------------------------------------- owner lookup
OWNERS = [PS, PN, RM]


@pytest.mark.parametrize("q,status,name", [
    ("Rahul", "found", "Rahul Mehta"), ("  RAHUL  ", "found", "Rahul Mehta"),
    ("Rahul Mehta", "found", "Rahul Mehta"), ("RAHUL@X.COM", "found", "Rahul Mehta"),
    ("Priya Sharma", "found", "Priya Sharma"), ("pn@x.com", "found", "Priya Nair"),
    ("Anita", "not_found", None), ("Pri", "not_found", None), ("", "not_found", None),
    ("   ", "not_found", None), ("unassigned", "unassigned", None),
    ("(unassigned)", "unassigned", None), ("UNASSIGNED", "unassigned", None),
])
def test_ol(q, status, name):
    r = lookup_owner(q, OWNERS)
    assert r.status == status and (r.person.name if r.person else None) == name


def test_ol_ambiguous_and_edge():
    r = lookup_owner("Priya", OWNERS)
    assert r.status == "ambiguous" and [p.name for p in r.candidates] == ["Priya Nair", "Priya Sharma"]
    sams = [Person("Sam Lee", "a@x"), Person("Sam Lee", "b@x")]
    assert lookup_owner("Sam Lee", sams).status == "ambiguous"
    assert lookup_owner("b@x", sams).person == sams[1]
    assert lookup_owner("Dev", [Person("Dev Patel")]).status == "found"
    assert lookup_owner("x", []).status == "not_found"


# ------------------------------------------------------------------ list
def seed(store):
    rows = [  # id, owner, due, status
        (PS, date(2026, 10, 10), "open"), (PS, date(2026, 10, 15), "open"),
        (RM, date(2026, 10, 20), "open"), (RM, date(2026, 10, 1), "done"),
        (None, None, "open"), (PN, date(2026, 10, 12), "open"), (RM, None, "open"),
    ]
    for n, (o, d, s) in enumerate(rows, 1):
        store.add(Item(None, o, f"task {n}", f"task {n}", d, s, "notes/a.md", date(2026, 10, 1), f"k{n}"))


@pytest.fixture
def store():
    s = Store(":memory:")
    seed(s)
    yield s
    s.close()


def ids(r):
    return [i.id for i in r.items]


def test_tl_filters(store):
    assert ids(list_items(store, TODAY)) == [1, 6, 4, 2, 3, 5, 7]
    assert ids(list_items(store, TODAY, status="overdue")) == [1, 6]
    assert ids(list_items(store, TODAY, status="open")) == [1, 6, 2, 3, 5, 7]
    assert ids(list_items(store, TODAY, status="done")) == [4]
    assert ids(list_items(store, TODAY, due_before=date(2026, 10, 16))) == [1, 6, 4, 2]
    assert ids(list_items(store, TODAY, owner="Rahul", due_before=date(2026, 10, 25))) == [4, 3]
    assert ids(list_items(store, TODAY, owner="Priya Sharma")) == [1, 2]
    assert ids(list_items(store, TODAY, owner="ps@x.com")) == [1, 2]
    assert ids(list_items(store, TODAY, owner="unassigned")) == [5]
    assert ids(list_items(store, TODAY, owner="Rahul", status="overdue")) == []


def test_tl_owner_errors(store):
    r = list_items(store, TODAY, owner="Priya")
    assert r.status == "ambiguous_owner" and not r.items and len(r.candidates) == 2
    assert list_items(store, TODAY, owner="Anita").status == "owner_not_found"


def test_tl_format(store):
    out = format_table(list_items(store, TODAY).items, TODAY).splitlines()
    assert out[0].split() == ["ID", "OWNER", "TASK", "DUE", "STATUS", "SOURCE"]
    assert len(out) == 8
    assert "overdue" in out[1] and "task 1" in out[1]
    row = {l.split()[0]: l for l in out[1:]}
    assert "open" in row["2"] and "overdue" not in row["2"]  # due today
    assert "(unassigned)" in row["5"] and "—" in row["5"] and "overdue" not in row["5"]
    assert row["1"].rstrip().endswith("a.md")


def test_tl_format_edges():
    assert format_table([], TODAY) == "No items match"
    long = Item(1, None, "x" * 100, "x", None, "open", "a.md", TODAY, "k", ["b.md", "c.md"])
    row = format_table([long], TODAY).splitlines()[1]
    assert "x" * 59 + "…" in row and "x" * 60 not in row and row.endswith("a.md (+2)")
    s = Store(":memory:")
    assert list_items(s, TODAY).items == []
    s.close()


# ------------------------------------------------------------------ done
def test_td(store):
    now = datetime(2026, 10, 15, 9, 0)
    r = mark_done(store, 1, now)
    assert r.outcome == "done" and r.item.done_at == now and "task 1" in r.message
    assert not is_overdue(store.get(1), TODAY)
    assert 1 not in ids(list_items(store, TODAY, status="open"))
    r2 = mark_done(store, 1, datetime(2027, 1, 1))
    assert r2.outcome == "already_done" and store.get(1).done_at == now
    r3 = mark_done(store, 999, now)
    assert r3.outcome == "not_found" and r3.message == "No item with id 999" and r3.item is None
    assert store.get(2).status == "open"


# --------------------------------------------------------------- compose
def it(id, due, status="open", owner=RM, task="t", src="notes/standup.md"):
    return Item(id, owner, task, task, due, status, src, date(2026, 10, 12), f"k{id}")


def test_fc_sections_and_order():
    items = [it(3, None), it(2, date(2026, 10, 20)), it(1, date(2026, 10, 10)), it(4, date(2026, 10, 15))]
    d = compose(RM, items, TODAY)
    assert d.to == "rahul@x.com"
    assert d.subject == "Action items follow-up — Rahul — 2026-10-15"
    assert d.body.startswith("Hi Rahul,") and d.body.rstrip().endswith("Thanks,")
    assert d.body.index("Overdue") < d.body.index("Open")
    assert d.included_ids == (1, 4, 2, 3)  # overdue; then due asc (today before 20th), undated last
    assert "5 days overdue" in d.body and "no due date" in d.body
    assert "due Sat 10 Oct 2026" in d.body and "standup, 2026-10-12" in d.body
    assert d.body.count("(from") == 4


def test_fc_single_section_and_none():
    assert "Overdue" not in compose(RM, [it(1, date(2026, 10, 20))], TODAY).body
    assert "\nOpen" not in compose(RM, [it(1, date(2026, 10, 1))], TODAY).body
    assert compose(RM, [], TODAY) is None
    assert compose(RM, [it(1, None, "done")], TODAY) is None


def test_fc_filters_and_cleanup():
    d = compose(RM, [it(1, None), it(1, None), it(2, None, owner=PS)], TODAY)
    assert d.included_ids == (1,)
    assert compose(Person("Dev Patel"), [it(1, None, owner=Person("Dev Patel"))], TODAY).to is None
    d = compose(RM, [it(1, None, task="fix   it\nnow")], TODAY)
    assert "- fix it now — no due date" in d.body


@pytest.mark.parametrize("mod,allowed", [
    ("track_owner_lookup", set()), ("followup_compose", set()), ("track_list", {"core_store"}),
    ("track_done", {"core_store"}),
])
def test_imports(mod, allowed):
    ok = set(sys.stdlib_module_names) | {"core_models"} | allowed
    for n in ast.walk(ast.parse((SRC / f"{mod}.py").read_text())):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
            [n.module] if isinstance(n, ast.ImportFrom) else []
        for m in mods:
            assert m.split(".")[0] in ok | {"track_owner_lookup"} or m == "__future__", m
