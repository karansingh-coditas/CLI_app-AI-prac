"""Resolve a user-typed owner string to exactly one stored Person (pure)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .core_models import Person, norm_name


@dataclass(frozen=True)
class LookupResult:
    status: Literal["found", "ambiguous", "not_found", "unassigned"]
    person: Person | None = None
    candidates: tuple[Person, ...] = ()


def _pick(hits: list[Person]) -> LookupResult | None:
    if len(hits) == 1:
        return LookupResult("found", hits[0])
    if hits:
        return LookupResult("ambiguous", None, tuple(sorted(hits, key=lambda p: (p.name, p.email or ""))))
    return None


def lookup_owner(query: str, owners: Sequence[Person]) -> LookupResult:
    q = norm_name(query or "")
    if not q:
        return LookupResult("not_found")
    if q in ("unassigned", "(unassigned)"):
        return LookupResult("unassigned")
    for match in (
        lambda p: p.email is not None and p.email.lower() == q,
        lambda p: norm_name(p.name) == q,
        lambda p: p.first_name.lower() == q,
    ):
        if (r := _pick([p for p in owners if match(p)])):
            return r
    return LookupResult("not_found")
