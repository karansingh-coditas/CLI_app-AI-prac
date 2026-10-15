# core_store — Test Cases

| ID | Given | When | Then |
|---|---|---|---|
| CS-T1 | no DB file | `Store(path)` | file and schema created; `user_version == 1` |
| CS-T2 | new `Item` | `add` then `get(id)` | all fields round-trip (incl. `None` owner, `None` due, lists) |
| CS-T3 | two items added | compare ids | ids are distinct small integers |
| CS-T4 | item with key K stored | `add` another item with key K | integrity error surfaced (UNIQUE guard) |
| CS-T5 | stored item | `find_by_key(K)` / unknown key | item / `None` |
| CS-T6 | items of owners A, B and unassigned | `query(owner_key=A.key)` | only A's items |
| CS-T7 | same data | `query(owner_key="unassigned")` | only ownerless items |
| CS-T8 | items due 10-10, 10-20, `None` | `query(due_before=2026-10-15)` | only the 10-10 item |
| CS-T9 | open and done items | `query(status="done")` | only done items |
| CS-T10 | combined filters | `query(owner, status, due_before)` | AND of all filters |
| CS-T11 | owners with same first name but different emails | `owners()` | both returned, distinct |
| CS-T12 | open item | `mark_done(id, now)` | returns `done`; `done_at == now`; status done |
| CS-T13 | done item | `mark_done` again | returns `already_done`; `done_at` unchanged |
| CS-T14 | unknown id | `mark_done` | returns `not_found`; no change |
| CS-T15 | `with store.atomic():` add item then raise | exception propagates | item not persisted |
| CS-T16 | nested `atomic()` | inner raises, outer catches nothing | everything rolled back |
| CS-T17 | `--db x`, env `ACTIONTRACK_DB=y` | `default_db_path` | `x`; with only env → `y`; neither → `./actiontrack.db` |
| CS-T18 | DB path in a non-existent/read-only directory | `Store(path)` | `AppError`, `exit_code == 1` |
| CS-T19 | 5,000 items | `query()` | completes well under 1 s |
| CS-T20 | task text containing `'` and `;` | `add`, `query` | stored and returned intact (no injection) |
