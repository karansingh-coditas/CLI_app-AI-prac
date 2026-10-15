"""Shared contracts: dataclasses, exceptions, exit codes, is_overdue, resolve_today."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Mapping

OK, RUNTIME_ERROR, USAGE_ERROR = 0, 1, 2


def norm_name(s: str) -> str:
    return " ".join(s.lower().split())


@dataclass(frozen=True)
class Person:
    name: str
    email: str | None = None

    @property
    def key(self) -> str:
        return self.email.strip().lower() if self.email else norm_name(self.name)

    @property
    def first_name(self) -> str:
        parts = self.name.split()
        return parts[0] if parts else ""

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Person) and self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)


@dataclass(frozen=True)
class RawItemLine:
    text: str
    checked: bool
    line_no: int


@dataclass(frozen=True)
class Note:
    path: str
    date: date
    attendees: tuple[Person, ...]
    lines: tuple[RawItemLine, ...]
    # lines that look like action items but are not `- [ ]` checkboxes (reported, never stored)
    unrecognised: tuple[RawItemLine, ...] = ()


@dataclass
class Item:
    id: int | None
    owner: Person | None
    task: str
    raw_text: str
    due_date: date | None
    status: Literal["open", "done"]
    source_file: str
    source_date: date
    dedup_key: str
    also_seen_in: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    done_at: datetime | None = None


@dataclass(frozen=True)
class Issue:
    file: str
    line: int | None
    code: str  # MALFORMED_NOTE, AMBIGUOUS_OWNER, UNKNOWN_OWNER, BAD_DUE_DATE, DUE_CHANGED, UNPARSEABLE_ITEM
    message: str


@dataclass(frozen=True)
class Draft:
    to: str | None
    subject: str
    body: str
    included_ids: tuple[int, ...]


@dataclass(frozen=True)
class DraftResult:
    draft_id: str
    link: str | None = None


class MalformedNote(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class AppError(Exception):
    """Expected, user-facing failure."""

    def __init__(self, message: str, exit_code: int = RUNTIME_ERROR):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def is_overdue(item: Item, today: date) -> bool:
    return item.status == "open" and item.due_date is not None and item.due_date < today


def resolve_today(cli_value: str | None, env: Mapping[str, str]) -> date:
    raw = cli_value or env.get("ACTIONTRACK_TODAY")
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise AppError(f"invalid date for today: {raw!r} (expected YYYY-MM-DD)", USAGE_ERROR) from None
