# track_done — Spec

**Family:** `track_` · **File:** `src/actiontrack/track_done.py` · **Depends on:** `core_models`, `core_store`

## Purpose
Implement `actiontrack done <id>`: mark one stored item as done.

## Requirements covered
FR-D1, FR-D2, FR-D3, FR-D4. Acceptance: AC-9.

## Public interface

```python
@dataclass(frozen=True)
class DoneResult:
    outcome: Literal["done", "already_done", "not_found"]
    item: Item | None            # the item after the call (None when not_found)
    message: str                 # user-facing line

def mark_done(store: Store, item_id: int, now: datetime) -> DoneResult
```

## Rules
1. Unknown id → `not_found`, message `No item with id <id>`, **no change**. Exit code mapping is below.
2. Open item → status `done`, `done_at = now`, message `Marked #<id> done: <task>`.
3. Already done → `already_done`, nothing changes (`done_at` preserved), message `#<id> was already done`.
4. Only the database is changed. Source `.md` files are never touched (FR-D4).
5. Because `ingest_dedup.merge` never reopens `done` items, a later `ingest` keeps the item done.

## Exit-code mapping (done by `cli_app`)
`done` → 0 · `already_done` → 0 · `not_found` → 2 (bad argument).

## Validation
`item_id` is an `int` — `cli_app` rejects non-integers as usage errors (exit 2) before calling this module.

## Out of scope
Un-doing/reopening items, bulk done, marking by task text.
