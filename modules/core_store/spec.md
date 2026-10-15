# core_store — Spec

**Family:** `core_` · **File:** `src/actiontrack/core_store.py` · **Depends on:** `core_models`, stdlib `sqlite3`

## Purpose
The only module that talks to SQLite. Gives every other module a small repository API for `Item`s.

## Requirements covered
FR-I2 (persist, DB path), FR-I3 (no duplicate rows), FR-D1 (done_at), NFR-2 (atomic, no corruption), NFR-4 (speed).

## Public interface

```python
class Store:
    def __init__(self, path: str)                       # creates file + schema if missing
    def atomic(self) -> ContextManager[None]            # one transaction; rollback on exception
    def add(self, item: Item) -> Item                   # assigns id, created_at
    def update(self, item: Item) -> None                # by id
    def get(self, item_id: int) -> Item | None
    def find_by_key(self, dedup_key: str) -> Item | None
    def query(self, owner_key: str | None = None,       # Person.key, or "unassigned"
              status: Literal["open","done"] | None = None,
              due_before: date | None = None) -> list[Item]
    def owners(self) -> list[Person]                    # distinct non-null owners
    def mark_done(self, item_id: int, now: datetime) -> Literal["done","already_done","not_found"]
    def close(self) -> None

def default_db_path(cli_value: str | None, env: Mapping[str, str]) -> str
```

## Rules
- DB path precedence: `--db` value, env `ACTIONTRACK_DB`, then `./actiontrack.db`.
- Schema: one `items` table. `id INTEGER PRIMARY KEY AUTOINCREMENT` (small, typeable). `dedup_key` has a **UNIQUE** index so a duplicate row cannot exist even if a caller forgets to merge.
- `owner_email`, `owner_name` stored as columns. `also_seen_in` and `notes` stored as JSON text. Dates stored as ISO strings.
- `query(due_before=D)` excludes items with `due_date IS NULL`. `owner_key="unassigned"` returns items with no owner.
- `query` returns rows ordered by `id`. Sorting for display belongs to `track_list`.
- `atomic()` nests safely (a nested call joins the outer transaction).
- Items are never deleted in v1.
- DB not creatable / not writable → `AppError(exit_code=1)`.

## Out of scope
Dedup logic, merge rules, overdue computation, display ordering, migrations (schema version stored in `PRAGMA user_version = 1` for later).
