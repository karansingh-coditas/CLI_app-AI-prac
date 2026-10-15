# core_store — Plan

## Approach
Thin wrapper over stdlib `sqlite3`. No ORM. Row ↔ `Item` conversion in two private helpers.

## Design decisions
- **UNIQUE `dedup_key`** is the last-line guarantee for FR-I3 (idempotent ingest).
- **Owner identity:** store `owner_key` (indexed) alongside name/email so `query(owner_key=…)` is a plain equality match.
- **JSON text** for `also_seen_in` / `notes`: small lists, never queried.
- **Transactions:** use `isolation_level=None` and explicit `BEGIN`/`COMMIT`, with a depth counter for nested `atomic()`.
- `PRAGMA foreign_keys` unnecessary (one table). `PRAGMA user_version = 1` for future migrations.

## Steps
1. Schema creation + `PRAGMA user_version`.
2. `add` / `get` / `update` with row mapping.
3. `find_by_key`, `query` (dynamic WHERE built from non-None filters, parameterised).
4. `owners`, `mark_done`.
5. `atomic()` context manager.
6. `default_db_path`.
7. Tests against `:memory:` and a temp file.

## Risks
- SQL injection: mitigated by parameterised queries only.
- Windows file locking on the DB: always `close()` in tests (use a fixture).
- Date round-trip errors: test ISO conversion for `None` and real dates.

## Definition of done
All `test-cases.md` pass; no SQL outside this module.
