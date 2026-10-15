# ingest_runner — Plan

## Approach
A short loop that glues four pure modules and the store together. All rules live in those modules; this one only sequences and counts.

## Design decisions
- **One transaction per file** (`store.atomic()`): a bad note or crash never leaves partial data from that file (FR-E16, NFR-2).
- **Order independent result:** files sorted by name for determinism, but `merge` picks primary source by date, so the outcome doesn't depend on order.
- **Store receives collaborators as arguments** (`store`, `now`) so tests can use `:memory:` and a fixed clock.
- **`format_report` is separate** from `run_ingest` so tests assert on data, and the CLI decides where text goes.
- **Wide `except Exception` only around one file's processing**, converting to an `Issue`. Fatal setup errors (folder, DB) still surface as `AppError`.

## Steps
1. Folder validation + `*.md` listing.
2. File read/decode with error mapping.
3. Per-line pipeline (owner → due → item build → dedup key).
4. Add/merge/update/skip branch with counters.
5. Report object + `format_report`.
6. Integration tests using `tests/fixtures/notes/` (shared fixtures with `ingest_note_parser`).

## Risks
- Counting semantics drifting from the spec: lock them with tests in `test-cases.md`.
- Large folders: 500 notes / 5,000 items < 10 s requires the single-transaction-per-file model and indexed `dedup_key` lookups (already in `core_store`).
- A catch-all `except` can hide bugs. Mitigation: include the exception type in the `Issue` message and log the traceback when `--verbose`.

## Definition of done
All `test-cases.md` pass, including idempotent re-run and the performance case.
