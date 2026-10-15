"""Parse the text of one meeting-note .md file into a Note (pure, no file I/O).

Two header styles are accepted: YAML front matter (`---` fenced) or plain header lines
(`Date: ...` / `Attendees: a, b`) before the first blank line.
"""
from __future__ import annotations

import re
from datetime import date, datetime

import yaml

from .core_models import MalformedNote, Note, Person, RawItemLine

_ITEM = re.compile(r"^\s*[-*+]\s+\[( |x|X)\]\s+(\S.*?)\s*$")
_ACTION_LINE = re.compile(r"^\s*(?:ACTION(?: ITEM)?S?|TODO)\s*:\s*(\S.*?)\s*$", re.I)
_HEADER = re.compile(r"^(date|attendees)\s*:\s*(.*?)\s*$", re.I)
_ATTENDEE = re.compile(r"^(?P<name>[^<]+?)\s*(?:<(?P<email>[^>]*)>)?$")
_WEEKDAY_PREFIX = re.compile(r"^(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\.?,?\s+", re.I)
_DATE_FORMATS = ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y")
_COMMENT = re.compile(r"<!--.*?-->", re.S)


def _parse_date(v: object) -> date:
    if isinstance(v, str):
        s = _WEEKDAY_PREFIX.sub("", v.strip())
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                pass
    elif isinstance(v, date) and not isinstance(v, datetime):
        return v
    raise MalformedNote("missing or invalid date")


def _parse_attendees(v: object) -> tuple[Person, ...]:
    if isinstance(v, str):  # header style "A, B <b@x.com>"
        v = [e for e in re.split(r",(?![^<]*>)", v) if e.strip()]
    if not isinstance(v, list) or not v:
        raise MalformedNote("missing or empty attendees")
    people: dict[str, Person] = {}
    for entry in v:
        m = _ATTENDEE.match(entry.strip()) if isinstance(entry, str) else None
        if not m:
            raise MalformedNote("invalid attendee entry")
        name = " ".join(m["name"].split())
        email = (m["email"] or "").strip() or None
        p = Person(name, email)
        people.setdefault(p.key, p)
    return tuple(people.values())


def _front_matter(lines: list[str]) -> tuple[dict, int]:
    """Return (fields, index of first body line)."""
    if lines[0].rstrip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
        if end is None:
            raise MalformedNote("missing front matter")
        try:
            fm = yaml.safe_load("\n".join(lines[1:end]))
        except Exception:  # YAMLError, or ValueError for impossible dates like 2026-13-45
            raise MalformedNote("invalid front matter") from None
        if not isinstance(fm, dict):
            raise MalformedNote("invalid front matter")
        return {k.lower(): v for k, v in fm.items() if isinstance(k, str)}, end + 1
    fields: dict = {}
    i = next((n for n, l in enumerate(lines) if l.strip()), 0)  # skip leading blank lines
    while i < len(lines) and lines[i].strip():
        m = _HEADER.match(lines[i].strip())
        if m:
            fields.setdefault(m[1].lower(), m[2])
        i += 1
    if not fields:
        raise MalformedNote("missing front matter")
    return fields, i


def _scan_body(lines: list[str], start: int) -> tuple[list[RawItemLine], list[RawItemLine]]:
    body = _COMMENT.sub(lambda m: "\n" * m[0].count("\n"), "\n".join(lines[start:])).split("\n")
    items, unrecognised = [], []
    in_fence, table = False, None  # table: None = outside, else True if it is an "action" table
    for n, line in enumerate(body, start + 1):
        s = line.strip()
        if s.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if s.startswith("|"):
            if table is None:
                table = "action" in s.lower()
            elif table and not re.fullmatch(r"[|\-:\s]+", s):
                unrecognised.append(RawItemLine(s, False, n))
            continue
        table = None
        if m := _ITEM.match(line):
            items.append(RawItemLine(m.group(2), m.group(1) in "xX", n))
        elif m := _ACTION_LINE.match(line):
            unrecognised.append(RawItemLine(m.group(1), False, n))
    return items, unrecognised


def parse_note(path: str, text: str) -> Note:
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise MalformedNote("empty file")
    lines = text.split("\n")
    fields, body_start = _front_matter(lines)
    when = _parse_date(fields.get("date"))
    attendees = _parse_attendees(fields.get("attendees"))
    items, unrecognised = _scan_body(lines, body_start)
    return Note(path, when, attendees, tuple(items), tuple(unrecognised))
