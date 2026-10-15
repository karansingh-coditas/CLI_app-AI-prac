# ingest_owner_resolver — Spec

**Family:** `ingest_` · **File:** `src/actiontrack/ingest_owner_resolver.py` · **Depends on:** `core_models` only

## Purpose
From one item's text and the note's attendee list, decide who owns the item and return the remaining task text. Pure function.

## Requirements covered
FR-P1, FR-E10, FR-E11, FR-E12, FR-E14, FR-E18 (partial), FR-E13 (uses `Person.key`).

## Public interface

```python
@dataclass(frozen=True)
class OwnerResult:
    owner: Person | None
    task_text: str                       # text with the owner prefix removed (if owner resolved)
    status: Literal["resolved", "none", "ambiguous", "unknown"]
    candidates: tuple[Person, ...] = ()  # filled when ambiguous
    note: str | None = None              # human-readable, stored on Item.notes

def resolve_owner(text: str, attendees: Sequence[Person]) -> OwnerResult
```

## Rules
1. **Pattern** (anchored at the start of the text): `^<name> (to|will) <rest>` where `<name>` is 1–3 words, each starting with a letter. A trailing `.` on a word is allowed (`Priya S.`). Matching `to`/`will` is case-insensitive. `<rest>` must be non-empty.
2. No match → `status="none"`, `owner=None`, `task_text=text` unchanged.
3. Name matching against attendees, case-insensitive, in this order:
   1. Exact full name → that attendee.
   2. One word + surname initial (`Priya S.`) → attendees whose first name matches and surname starts with the initial.
   3. Single word → attendees whose first name matches.
4. Outcome of matching:
   - Exactly **one** candidate → `resolved`, `owner=candidate`, `task_text=<rest>`.
   - **More than one** → `ambiguous`, `owner=None`, `candidates` set, `task_text=text` unchanged, `note="ambiguous owner: Priya (Priya Sharma | Priya Nair)"`.
   - **Zero** → `unknown`, `owner=None`, `task_text=text` unchanged, `note="unknown owner: <Name> is not an attendee"`.
5. Full-name collision (two attendees with the same full name but different emails) → `ambiguous`.
6. Never raises. Never consults any note other than the attendee list passed in (FR-E10).
7. A name appearing mid-sentence (`Ask Priya to review`) is **not** an owner match (pattern is anchored).

## Out of scope
Cross-note identity, due dates, deciding what to do with ambiguous/unknown items (the runner stores them unassigned and reports).

## Amendment — real sample notes (2026-10-15)
- `@anita: <rest>` mention form resolves like `Anita to <rest>`.
- A parenthetical after the name is ignored for matching: `Lena (with Priya) to …` → Lena.
- Placeholder owners (`Everyone`, `Team`, `Someone`, `TBD`, `Anyone`, `We`, …) → `none` (unassigned, no warning).
- Multi-word text that is not a name but contains an attendee's first name (`Ask Priya to …`) → `none`.
