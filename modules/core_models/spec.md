# core_models — Spec

**Family:** `core_` · **File:** `src/actiontrack/core_models.py` · **Depends on:** stdlib only

## Purpose
The single shared vocabulary. Every other module exchanges data using these types, so no module needs to know another's internals.

## Requirements covered
FR-E13 (person identity), FR-L3 (overdue definition), NFR-7 (exit codes), NFR-8 (injectable today), NFR-10 (date-only).

## Public interface

```python
@dataclass(frozen=True)
class Person:
    name: str
    email: str | None = None
    key: str          # property: lower(email) if email else norm_name(name)
    first_name: str   # property
    # __eq__/__hash__ use .key only

def norm_name(s: str) -> str          # lower-case, collapse whitespace, strip

@dataclass(frozen=True)
class RawItemLine: text: str; checked: bool; line_no: int

@dataclass(frozen=True)
class Note: path: str; date: date; attendees: tuple[Person, ...]; lines: tuple[RawItemLine, ...]

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
    also_seen_in: list[str]
    notes: list[str]            # e.g. "ambiguous owner: Priya (Priya Sharma | Priya Nair)"
    created_at: datetime | None
    done_at: datetime | None

@dataclass(frozen=True)
class Issue: file: str; line: int | None; code: str; message: str
# codes: MALFORMED_NOTE, AMBIGUOUS_OWNER, UNKNOWN_OWNER, BAD_DUE_DATE, DUE_CHANGED, UNPARSEABLE_ITEM

@dataclass(frozen=True)
class Draft: to: str | None; subject: str; body: str; included_ids: tuple[int, ...]
@dataclass(frozen=True)
class DraftResult: draft_id: str; link: str | None = None

class MalformedNote(Exception): reason: str
class AppError(Exception): message: str; exit_code: int   # expected, user-facing failure

OK, RUNTIME_ERROR, USAGE_ERROR = 0, 1, 2

def is_overdue(item: Item, today: date) -> bool
def resolve_today(cli_value: str | None, env: Mapping[str, str]) -> date
```

## Rules
- `is_overdue` = `status == "open"` and `due_date is not None` and `due_date < today`. Due today is **not** overdue.
- `resolve_today` precedence: `--today` value, then env `ACTIONTRACK_TODAY`, then `date.today()`. Invalid value → `AppError(exit_code=2)`.
- `Person.key` makes two people sharing a first name distinct (different email or full name) and the same person equal across notes.
- No I/O, no global state, no third-party imports.

## Out of scope
Parsing, persistence, formatting, business rules other than `is_overdue`.

## Amendment (2026-10-15)
`Note` gains `unrecognised: tuple[RawItemLine, ...] = ()` — lines that look like action items but are not checkboxes (see `ingest_note_parser`).
