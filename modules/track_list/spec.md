# track_list — Spec

**Family:** `track_` · **File:** `src/actiontrack/track_list.py`
**Depends on:** `core_models`, `core_store`, `track_owner_lookup`

## Purpose
Implement `actiontrack list`: filter stored items, order them, render a table.

## Requirements covered
FR-L1–L5, FR-E7 (list unassigned), FR-E8 (undated items never overdue), FR-E15, FR-E4 (no duplicates in output). Acceptance: AC-7, AC-8.

## Public interface

```python
@dataclass
class ListResult:
    items: list[Item]
    status: Literal["ok", "ambiguous_owner", "owner_not_found"]
    candidates: tuple[Person, ...] = ()

def list_items(store: Store, today: date,
               owner: str | None = None,
               status: Literal["open", "done", "overdue"] | None = None,
               due_before: date | None = None) -> ListResult

def format_table(items: Sequence[Item], today: date) -> str    # "No items match" when empty
```

## Rules
1. **Owner:** if given, `lookup_owner(owner, store.owners())`. `found` → filter by `person.key`. `unassigned` → items with no owner. `ambiguous` / `not_found` → return that status with no items. The caller prints the candidates and exits 2.
2. **Status filter:**
   - `open` → `status == open` (includes overdue, FR-L3).
   - `done` → `status == done`.
   - `overdue` → `is_overdue(item, today)`.
   - none → all items.
3. **`due_before D`:** only items whose `due_date < D`. Items without a due date are excluded.
4. Filters combine with AND.
5. **Ordering:** overdue first; then by `due_date` ascending; undated last; ties by `id`.
6. **Display status:** an open item for which `is_overdue` is true displays `overdue`; otherwise `open` / `done`.
7. **Table columns:** `ID  OWNER  TASK  DUE  STATUS  SOURCE`. Missing owner → `(unassigned)`. Missing due date → `—`. `SOURCE` is the file name; if `also_seen_in` is non-empty add ` (+N)`. Long tasks are truncated with `…` at 60 chars.
8. Output has one row per item (merged duplicates already one row).
9. Empty result → `No items match` (exit 0).

## Out of scope
Parsing date arguments (done in `cli_app`), JSON/CSV output, pagination.
