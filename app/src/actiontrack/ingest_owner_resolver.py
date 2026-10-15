"""Decide who owns an action item from its text and the note's attendees (pure)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Sequence

from .core_models import Person, norm_name

_WORD = r"[^\W\d_][\w'’-]*\.?"
_PREFIX = re.compile(  # "Priya to ...", "Priya S. will ...", "Lena (with Priya) to ..."
    rf"^(?P<name>{_WORD}(?:\s+{_WORD}){{0,2}}?)(?:\s*\([^)]*\))?\s+(?:to|will)\s+(?P<rest>\S.*)$",
    re.IGNORECASE | re.DOTALL,
)
_MENTION = re.compile(r"^@(?P<name>[^\W\d_][\w'’-]*)[:,]?\s+(?P<rest>\S.*)$", re.DOTALL)  # "@anita: audit ..."
_NOBODY = {"everyone", "everybody", "team", "someone", "somebody", "anyone", "tbd", "all", "we"}


@dataclass(frozen=True)
class OwnerResult:
    owner: Person | None
    task_text: str
    status: Literal["resolved", "none", "ambiguous", "unknown"]
    candidates: tuple[Person, ...] = ()
    note: str | None = None


def _match(name: str, attendees: Sequence[Person]) -> list[Person]:
    words = name.split()
    full = norm_name(name.rstrip("."))
    hit = [p for p in attendees if norm_name(p.name) == full]
    if hit:
        return hit
    first = words[0].lower().rstrip(".")
    if len(words) == 2 and len(words[1].rstrip(".")) == 1:
        initial = words[1][0].lower()
        return [p for p in attendees
                if p.first_name.lower() == first and p.name.split()[-1].lower().startswith(initial)
                and len(p.name.split()) > 1]
    if len(words) == 1:
        return [p for p in attendees if p.first_name.lower() == first]
    return []


def resolve_owner(text: str, attendees: Sequence[Person]) -> OwnerResult:
    m = _MENTION.match(text.strip()) or _PREFIX.match(text.strip())
    if not m or m["name"].lower() in _NOBODY:
        return OwnerResult(None, text, "none")
    name, rest = m["name"], m["rest"].strip()
    found = _match(name, attendees)
    if len(found) == 1:
        return OwnerResult(found[0], rest, "resolved")
    if found:
        names = " | ".join(p.name for p in found)
        return OwnerResult(None, text, "ambiguous", tuple(found),
                           f"ambiguous owner: {name} ({names})")
    if len(name.split()) > 1 and any(p.first_name.lower() in name.lower().split() for p in attendees):
        return OwnerResult(None, text, "none")  # attendee named mid-sentence: "Ask Priya to ..."
    return OwnerResult(None, text, "unknown", note=f"unknown owner: {name} is not an attendee")
