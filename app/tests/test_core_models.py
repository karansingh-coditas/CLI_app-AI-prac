import ast
import pathlib
import sys
from datetime import date

import pytest

from actiontrack.core_models import AppError, Item, Person, is_overdue, resolve_today


def item(status="open", due=date(2026, 10, 10)):
    return Item(None, None, "t", "t", due, status, "f.md", date(2026, 10, 1), "k")


def test_person_equality_case_insensitive_email():
    a, b = Person("Priya Sharma", "A@X.com"), Person("Priya Sharma", "a@x.com")
    assert a == b and hash(a) == hash(b)


def test_same_first_name_distinct():
    a, b = Person("Priya Sharma", "ps@x.com"), Person("Priya Nair", "pn@x.com")
    assert a != b and a.first_name == b.first_name == "Priya"


def test_key_normalised_name():
    assert Person("  Priya   Sharma ").key == "priya sharma"


def test_overdue():
    today = date(2026, 10, 15)
    assert is_overdue(item(), today)
    assert not is_overdue(item(due=today), today)
    assert not is_overdue(item(due=None), today)
    assert not is_overdue(item(status="done"), today)


def test_resolve_today():
    env = {"ACTIONTRACK_TODAY": "2026-02-03"}
    assert resolve_today("2026-01-05", env) == date(2026, 1, 5)
    assert resolve_today(None, env) == date(2026, 2, 3)
    assert resolve_today(None, {}) == date.today()
    with pytest.raises(AppError) as e:
        resolve_today("not-a-date", {})
    assert e.value.exit_code == 2


def test_stdlib_only():
    src = pathlib.Path(__file__).parents[1] / "src/actiontrack/core_models.py"
    for n in ast.walk(ast.parse(src.read_text())):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) else []
        for m in mods:
            assert m.split(".")[0] in sys.stdlib_module_names
