# core_store — Tasks

- [ ] CS-1 Create `core_store.py`; open connection, create `items` table with UNIQUE index on `dedup_key`, set `user_version = 1`
- [ ] CS-2 Row ↔ `Item` mapping helpers (ISO dates, JSON lists, nullable owner)
- [ ] CS-3 `add`, `get`, `update`
- [ ] CS-4 `find_by_key`
- [ ] CS-5 `query` with optional `owner_key` (incl. `"unassigned"`), `status`, `due_before` (NULL due excluded)
- [ ] CS-6 `owners()` distinct non-null owners
- [ ] CS-7 `mark_done` returning `done` / `already_done` / `not_found`, setting `done_at`
- [ ] CS-8 `atomic()` with rollback and nesting support
- [ ] CS-9 `default_db_path` precedence (CLI, env, default)
- [ ] CS-10 Convert `sqlite3.Error` on open/write to `AppError(exit_code=1)`
- [ ] CS-11 Write `tests/test_core_store.py` for all cases in `test-cases.md`
