"""Tests for ingest_note_parser, ingest_owner_resolver, ingest_date_resolver, ingest_dedup."""
import ast
import pathlib
import sys
from datetime import date

import pytest

from actiontrack.core_models import Item, MalformedNote, Person
from actiontrack.ingest_date_resolver import resolve_due
from actiontrack.ingest_dedup import dedup_key, merge, normalise_task
from actiontrack.ingest_note_parser import parse_note
from actiontrack.ingest_owner_resolver import resolve_owner

SRC = pathlib.Path(__file__).parents[1] / "src/actiontrack"

# ---------------------------------------------------------------- note parser
GOOD = """---
date: 2026-10-12
attendees:
  - Priya Sharma <priya@x.com>
  - Rahul Mehta
---

text
- [ ] A
- [x] B
- [X] C
"""


def fm(front, body=""):
    return f"---\n{front}\n---\n{body}"


def test_np_valid():
    n = parse_note("n.md", GOOD)
    assert n.date == date(2026, 10, 12)
    assert n.attendees == (Person("Priya Sharma", "priya@x.com"), Person("Rahul Mehta"))
    assert n.attendees[0].email == "priya@x.com" and n.attendees[1].email is None
    assert [(l.text, l.checked, l.line_no) for l in n.lines] == [("A", False, 9), ("B", True, 10), ("C", True, 11)]


@pytest.mark.parametrize("text,reason", [
    ("no front matter\n- [ ] a", "missing front matter"),
    ("---\ndate: 2026-10-12\n", "missing front matter"),
    (fm("date: [unclosed"), "invalid front matter"),
    (fm("- a\n- b"), "invalid front matter"),
    (fm("attendees: [A B]"), "missing or invalid date"),
    (fm("date: 2026-13-45\nattendees: [A B]"), ""),
    (fm("date: 12 Oct\nattendees: [A B]"), "missing or invalid date"),
    (fm("date: 2026-10-12"), "missing or empty attendees"),
    (fm("date: 2026-10-12\nattendees: []"), "missing or empty attendees"),
    (fm("date: 2026-10-12\nattendees: [5]"), ""),
    (fm("date: 2026-10-12\nattendees: ['  ']"), ""),
    ("", "empty file"),
    ("  \n\n", "empty file"),
    (fm("x: !!python/object/apply:os.system ['echo hi']"), "invalid front matter"),
])
def test_np_malformed(text, reason):
    with pytest.raises(MalformedNote) as e:
        parse_note("n.md", text)
    assert reason in e.value.reason


def test_np_misc():
    base = parse_note("n.md", GOOD)
    assert parse_note("n.md", fm('date: "2026-10-12"\nattendees: [A B]')).date == date(2026, 10, 12)
    assert parse_note("n.md", "﻿" + GOOD.replace("\n", "\r\n")) == base
    assert parse_note("n.md", fm("date: 2026-10-12\nattendees: [A B]", "prose\n- plain\n- [ ]\n")).lines == ()
    assert parse_note("n.md", fm("date: 2026-10-12\nattendees: [A B, A B]")).attendees == (Person("A B"),)
    assert parse_note("n.md", fm("date: 2026-10-12\nattendees: [A B]", "  - [ ] nested")).lines[0].text == "nested"


# ------------------------------------------------------------- owner resolver
PS, PN, RM = Person("Priya Sharma", "ps@x"), Person("Priya Nair", "pn@x"), Person("Rahul Mehta", "r@x")
ONE = [PS, RM]
TWO = [PS, PN, RM]


@pytest.mark.parametrize("text,att,status,owner,task", [
    ("Priya to send the revised quote by Friday", ONE, "resolved", PS, "send the revised quote by Friday"),
    ("Rahul will share the deck", ONE, "resolved", RM, "share the deck"),
    ("priya TO send quote", ONE, "resolved", PS, "send quote"),
    ("Priya Sharma to send quote", ONE, "resolved", PS, "send quote"),
    ("Update the onboarding doc", ONE, "none", None, None),
    ("Ask Priya to review the draft", ONE, "none", None, None),
    ("Anita to book the room", ONE, "unknown", None, None),
    ("Priya to", ONE, "none", None, None),
    ("Priya to send quote", TWO, "ambiguous", None, None),
    ("Priya S. to send quote", TWO, "resolved", PS, "send quote"),
    ("Priya Nair to send quote", TWO, "resolved", PN, "send quote"),
    ("Priya N to send quote", TWO, "resolved", PN, "send quote"),
    ("Rahul to send quote", TWO, "resolved", RM, "send quote"),
    ("Sam Lee to fix", [Person("Sam Lee", "a@x"), Person("Sam Lee", "b@x")], "ambiguous", None, None),
    ("Mary-Jane to call", [Person("Mary-Jane O'Neil")], "resolved", Person("Mary-Jane O'Neil"), "call"),
    ("Zoë to call", [Person("Zoë Ünal")], "resolved", Person("Zoë Ünal"), "call"),
    ("Priya will send quote", ONE, "resolved", PS, "send quote"),
    ("Update to docs", ONE, "unknown", None, None),
    ("Priya to send", [], "unknown", None, None),
])
def test_or(text, att, status, owner, task):
    r = resolve_owner(text, att)
    assert r.status == status and r.owner == owner
    assert r.task_text == (task if task is not None else text)


def test_or_notes():
    r = resolve_owner("Priya to send quote", TWO)
    assert r.note == "ambiguous owner: Priya (Priya Sharma | Priya Nair)" and r.candidates == (PS, PN)
    assert "Anita" in resolve_owner("Anita to book", ONE).note


# -------------------------------------------------------------- date resolver
M1, M2, M3 = date(2026, 10, 12), date(2026, 10, 16), date(2026, 10, 17)


@pytest.mark.parametrize("text,meet,due,task", [
    ("send the revised quote by Friday", M1, date(2026, 10, 16), "send the revised quote"),
    ("send quote by Friday", M2, date(2026, 10, 23), "send quote"),
    ("send quote by Monday", M1, date(2026, 10, 19), "send quote"),
    ("send quote by Sat", M3, date(2026, 10, 24), "send quote"),
    ("fix bug by 2026-10-30", M1, date(2026, 10, 30), "fix bug"),
    ("fix bug by 30 Oct", M1, date(2026, 10, 30), "fix bug"),
    ("fix bug by Oct 30, 2027", M1, date(2027, 10, 30), "fix bug"),
    ("fix bug due 30 October 2026", M1, date(2026, 10, 30), "fix bug"),
    ("call client today", M1, M1, "call client"),
    ("call client by tomorrow", M2, date(2026, 10, 17), "call client"),
    ("plan sprint by next week", M1, date(2026, 10, 19), "plan sprint"),
    ("plan sprint by next week", M2, date(2026, 10, 19), "plan sprint"),
    ("finish report by end of week", M1, date(2026, 10, 16), "finish report"),
    ("finish report by end of week", M3, date(2026, 10, 23), "finish report"),
    ("finish report by end of month", M1, date(2026, 10, 31), "finish report"),
    ("finish report by eom", date(2028, 2, 10), date(2028, 2, 29), "finish report"),
    ("finish report before 20 Oct", M1, date(2026, 10, 20), "finish report"),
    ("ship it BY FRIDAY", M1, date(2026, 10, 16), "ship it"),
    ("ship it 2026-10-30", M1, date(2026, 10, 30), "ship it"),
    ("fix by 2026-10-30 and review by Friday", M1, date(2026, 10, 30), "fix and review by Friday"),
    ("by Friday", M1, date(2026, 10, 16), ""),
    ("send quote by Friday, then rest", M1, date(2026, 10, 16), "send quote, then rest"),
    # forms seen in the sample notes
    ("finalise copy by Oct 3rd", M1, date(2026, 10, 3), "finalise copy"),
    ("validate targets by 5th Oct", M1, date(2026, 10, 5), "validate targets"),
    ("finalise copy by Wed 16 Sep", date(2026, 9, 14), date(2026, 9, 16), "finalise copy"),
    ("schedule cutover for Saturday 10 Oct", date(2026, 9, 29), date(2026, 10, 10), "schedule cutover"),
    ("freeze invoice edits from 9 Oct", date(2026, 9, 29), date(2026, 10, 9), "freeze invoice edits"),
    ("draft test plan by end of next week", date(2026, 9, 3), date(2026, 9, 11), "draft test plan"),
    ("draft test plan by end of next week", M1, date(2026, 10, 23), "draft test plan"),
    ("start SSO spike by next Tuesday", date(2026, 10, 5), date(2026, 10, 13), "start SSO spike"),
    ("write postmortem by EOD tomorrow", M1, date(2026, 10, 13), "write postmortem"),
    ("circulate summary by EOD", M1, M1, "circulate summary"),
    ("propose rotation by mid-October", date(2026, 9, 30), date(2026, 10, 15), "propose rotation"),
    ("send revised quote to Acme — by Friday", date(2026, 9, 8), date(2026, 9, 11), "send revised quote to Acme"),
    ("cut costs by 10% — proposal by 2026-10-09", M1, date(2026, 10, 9), "cut costs by 10% — proposal"),
    ("run survey, results due 15 October", date(2026, 9, 30), date(2026, 10, 15), "run survey, results"),
])
def test_dr_resolved(text, meet, due, task):
    r = resolve_due(text, meet)
    assert (r.due, r.task_text, r.warning) == (due, task, None)


@pytest.mark.parametrize("text,warns", [
    ("update the doc", False),
    ("fix bug by 31 Feb", True),
    ("fix bug by Fiday", True),
    ("book venue by soon", False),
    ("rotate pager, on call by hand", False),
    ("fix bug by 32nd Oct", True),
    ("ship it by mid-nonsense", False),
])
def test_dr_unresolved(text, warns):
    r = resolve_due(text, M1)
    assert r.due is None and r.task_text == text and bool(r.warning) == warns
    if warns:
        assert "could not resolve due date" in r.warning


def test_dr_no_clock():
    src = (SRC / "ingest_date_resolver.py").read_text()
    assert "today()" not in src and "now()" not in src


# ---------------------------------------------------------------------- dedup
def it(owner=PS, task="x", src="a.md", sd=date(2026, 10, 5), due=None, status="open", notes=(), seen=()):
    return Item(1, owner, task, task, due, status, src, sd, dedup_key(owner, task), list(seen), list(notes))


def test_dd_keys():
    assert normalise_task("Send the Revised Quote!") == normalise_task("send the revised quote")
    assert normalise_task("fix   bug — now") == normalise_task("fix bug now")
    assert normalise_task("“Quote” review") == "quote review"
    assert dedup_key(PS, "a") == dedup_key(Person("Priya Sharma", "PS@x"), "a")
    assert dedup_key(PS, "a") != dedup_key(PN, "a") != dedup_key(None, "a")
    assert dedup_key(None, "a") == dedup_key(None, "a!")
    assert dedup_key(PS, "send quote") != dedup_key(PS, "email quote")


def test_dd_merge_sources():
    r = merge(it(), it(src="b.md", sd=date(2026, 10, 12)))
    assert (r.item.source_file, r.item.also_seen_in, r.changed) == ("a.md", ["b.md"], True)
    r = merge(it(src="b.md", sd=date(2026, 10, 12)), it(src="a.md"))
    assert (r.item.source_file, r.item.also_seen_in) == ("a.md", ["b.md"])
    r = merge(it(src="a.md"), it(src="b.md"))  # same-date tie
    assert (r.item.source_file, r.item.also_seen_in) == ("a.md", ["b.md"])
    again = merge(r.item, it(src="b.md"))
    assert again.item.also_seen_in == ["b.md"] and not again.changed


def test_dd_merge_status_due_notes():
    assert merge(it(), it(status="done")).item.status == "done"
    assert merge(it(status="done"), it()).item.status == "done"
    r = merge(it(), it(status="done"))
    assert r.item.status == "done"
    r = merge(it(due=date(2026, 10, 16)), it(due=date(2026, 10, 23)))
    assert r.item.due_date == date(2026, 10, 23) and [i.code for i in r.issues] == ["DUE_CHANGED"]
    r = merge(it(due=date(2026, 10, 23)), it(due=date(2026, 10, 16)))
    assert r.item.due_date == date(2026, 10, 23) and not r.issues
    r = merge(it(), it(due=date(2026, 10, 16)))
    assert r.item.due_date == date(2026, 10, 16) and not r.issues
    assert merge(it(due=date(2026, 10, 16)), it()).item.due_date == date(2026, 10, 16)
    assert merge(it(notes=["a", "b"]), it(notes=["b", "c"])).item.notes == ["a", "b", "c"]


def test_dd_idempotent_and_pure():
    a, b = it(notes=["n"]), it(src="b.md", sd=date(2026, 10, 12), due=date(2026, 10, 9))
    a0, b0 = it(notes=["n"]), it(src="b.md", sd=date(2026, 10, 12), due=date(2026, 10, 9))
    merge(a, b)
    assert a == a0 and b == b0
    assert not merge(it(), it()).changed


@pytest.mark.parametrize("mod", ["ingest_note_parser", "ingest_owner_resolver", "ingest_date_resolver", "ingest_dedup"])
def test_imports_allowed(mod):
    ok = {"yaml", "actiontrack"} | set(sys.stdlib_module_names)
    for n in ast.walk(ast.parse((SRC / f"{mod}.py").read_text())):
        mods = [a.name for a in n.names] if isinstance(n, ast.Import) else \
            [n.module] if isinstance(n, ast.ImportFrom) and not n.level else []
        for m in mods:
            assert m.split(".")[0] in ok


# ------------------------------------------------- sample-note formats (parser)
HEADER_NOTE = """# Meeting: Team standup
Date: Monday, 14 September 2026
Attendees: Priya Nair <pn@x.com>, Rahul Mehta, Anita Desai

## Discussion
text

## Action items
- [ ] a
* [ ] b
+ [X] c
  - [ ] nested d
"""


def test_np_header_style():
    n = parse_note("n.md", HEADER_NOTE)
    assert n.date == date(2026, 9, 14)
    assert n.attendees == (Person("Priya Nair", "pn@x.com"), Person("Rahul Mehta"), Person("Anita Desai"))
    assert n.attendees[0].email == "pn@x.com"
    assert [(l.text, l.checked, l.line_no) for l in n.lines] == [
        ("a", False, 9), ("b", False, 10), ("c", True, 11), ("nested d", False, 12)]


@pytest.mark.parametrize("d", ["9 September 2026", "Sep 9, 2026", "2026-09-09", "Wed, 9 Sep 2026"])
def test_np_date_forms(d):
    n = parse_note("n.md", f"# T\nDate: {d}\nAttendees: A B\n\n- [ ] x")
    assert n.date == date(2026, 9, 9)


@pytest.mark.parametrize("text,reason", [
    ("# T\nDate: sometime last week\nAttendees: A B\n", "missing or invalid date"),
    ("# T\nDate: 2026-09-23\n\n## Discussion\n- [ ] x", "missing or empty attendees"),
    ("- [ ] Sam to chase\n\nno header, no date, no attendees", "missing front matter"),
])
def test_np_header_style_malformed(text, reason):
    with pytest.raises(MalformedNote) as e:
        parse_note("n.md", text)
    assert e.value.reason == reason


def test_np_ignores_fences_comments_quotes_and_flags_other_actions():
    body = """## Discussion
> quoted
> - [ ] Karan to refund by Friday

```
# template
- [ ] Owner to remediate <date>
```

<!-- - [ ] Sam to buy tokens
- [ ] still inside the comment -->

- [ ] real one

| Owner | Action | Due |
|-------|--------|-----|
| Anita | Refresh the brand kit | 2026-10-09 |

ACTION: Karan to circulate the summary
| a | b |
|---|---|
| not | an action table |
"""
    n = parse_note("n.md", "# T\nDate: 2026-09-30\nAttendees: A B\n\n" + body)
    assert [(l.text, l.line_no) for l in n.lines] == [("real one", 17)]
    assert [(l.text, l.line_no) for l in n.unrecognised] == [
        ("| Anita | Refresh the brand kit | 2026-10-09 |", 21), ("Karan to circulate the summary", 23)]


# ----------------------------------------------- sample-note formats (owners)
def test_or_mention_paren_and_placeholders():
    att = [Person("Anita Desai"), Person("Lena Fischer"), Person("Priya Nair")]
    r = resolve_owner("@anita: audit colour contrast by Mon", att)
    assert r.status == "resolved" and r.owner.name == "Anita Desai" and r.task_text == "audit colour contrast by Mon"
    r = resolve_owner("Lena (with Priya) to collect user feedback", att)
    assert r.status == "resolved" and r.owner.name == "Lena Fischer" and r.task_text == "collect user feedback"
    assert resolve_owner("Anita & Lena to agree on the API", att).status == "none"
    for who in ("Everyone", "Team", "Someone", "TBD"):
        assert resolve_owner(f"{who} to do it", att).status == "none"
    assert resolve_owner("@nobody: do it", att).status == "unknown"
