import sqlite3
import time
from datetime import date, datetime

import pytest

from actiontrack.core_models import AppError, Item, Person
from actiontrack.core_store import Store, default_db_path

A, B = Person("Priya Sharma", "ps@x.com"), Person("Priya Nair", "pn@x.com")


def mk(key, owner=None, due=None, status="open", task="t"):
    return Item(None, owner, task, task, due, status, "f.md", date(2026, 10, 1), key,
                ["g.md"], ["n"])


@pytest.fixture
def store(tmp_path):
    s = Store(str(tmp_path / "t.db"))
    yield s
    s.close()


def test_schema_and_roundtrip(store):
    assert store._db.execute("PRAGMA user_version").fetchone()[0] == 1
    i = store.add(mk("k1", A, date(2026, 10, 10)))
    n = store.add(mk("k2"))
    assert n.id != i.id
    got = store.get(i.id)
    assert got.owner == A and got.owner.email == "ps@x.com" and got.due_date == date(2026, 10, 10)
    assert got.also_seen_in == ["g.md"] and got.notes == ["n"] and got.created_at
    g2 = store.get(n.id)
    assert g2.owner is None and g2.due_date is None


def test_unique_key(store):
    store.add(mk("k"))
    with pytest.raises(sqlite3.IntegrityError):
        store.add(mk("k"))


def test_find_by_key_and_update(store):
    i = store.add(mk("k"))
    assert store.find_by_key("k").id == i.id and store.find_by_key("zz") is None
    i.due_date, i.also_seen_in = date(2026, 11, 1), ["a", "b"]
    store.update(i)
    assert store.get(i.id).due_date == date(2026, 11, 1) and store.get(i.id).also_seen_in == ["a", "b"]


def test_query_filters(store):
    store.add(mk("1", A, date(2026, 10, 10)))
    store.add(mk("2", A, date(2026, 10, 20), "done"))
    store.add(mk("3", B, None))
    store.add(mk("4", None, date(2026, 10, 1)))
    assert len(store.query(owner_key=A.key)) == 2
    assert len(store.query(owner_key="unassigned")) == 1
    assert len(store.query(due_before=date(2026, 10, 15))) == 2  # null due excluded
    assert len(store.query(status="done")) == 1
    assert len(store.query(owner_key=A.key, status="open", due_before=date(2026, 10, 15))) == 1
    assert [i.id for i in store.query()] == [1, 2, 3, 4]


def test_owners_same_first_name(store):
    store.add(mk("1", A))
    store.add(mk("2", B))
    store.add(mk("3", A))
    store.add(mk("4"))
    assert set(store.owners()) == {A, B} and len(store.owners()) == 2


def test_mark_done(store):
    i = store.add(mk("k"))
    now = datetime(2026, 10, 15, 9, 0)
    assert store.mark_done(i.id, now) == "done"
    assert store.get(i.id).done_at == now and store.get(i.id).status == "done"
    assert store.mark_done(i.id, datetime(2027, 1, 1)) == "already_done"
    assert store.get(i.id).done_at == now
    assert store.mark_done(999, now) == "not_found"


def test_atomic_rollback_and_nesting(store):
    with pytest.raises(RuntimeError):
        with store.atomic():
            store.add(mk("k"))
            raise RuntimeError
    assert store.query() == []
    with pytest.raises(RuntimeError):
        with store.atomic():
            store.add(mk("a"))
            with store.atomic():
                store.add(mk("b"))
                raise RuntimeError
    assert store.query() == []
    with store.atomic():
        with store.atomic():
            store.add(mk("c"))
    assert len(store.query()) == 1


def test_default_db_path():
    assert default_db_path("x", {"ACTIONTRACK_DB": "y"}) == "x"
    assert default_db_path(None, {"ACTIONTRACK_DB": "y"}) == "y"
    assert default_db_path(None, {}) == "./actiontrack.db"


def test_bad_path(tmp_path):
    with pytest.raises(AppError) as e:
        Store(str(tmp_path / "nope" / "x.db"))
    assert e.value.exit_code == 1


def test_special_chars_and_speed(store):
    store.add(mk("q", task="it's; DROP TABLE items;--"))
    assert store.query()[0].task == "it's; DROP TABLE items;--"
    with store.atomic():
        for n in range(5000):
            store.add(mk(f"b{n}"))
    t = time.time()
    store.query()
    assert time.time() - t < 1
