# ingest_dedup — Plan

## Approach
Two tiny pure functions for the key, one pure `merge`. State lives in the store; this module only computes.

## Design decisions
- **Exact match after normalisation** (Q-7). A fuzzy matcher is a bigger decision with false-merge risk, so it is deferred.
- **`dedup_key` string** (not a tuple) so it is storable and indexable in `core_store` with a UNIQUE index.
- **Merge returns a new `Item`** (use `dataclasses.replace`) so tests and callers can diff before/after.
- **`changed` flag** lets the runner count "updated" vs "unchanged" accurately and keeps re-ingest idempotent.
- "Done wins" is expressed here once; neither `ingest_runner` nor `track_*` re-implements it.

## Steps
1. `normalise_task` (use `str.translate` with `string.punctuation` plus unicode punctuation via `unicodedata.category`).
2. `dedup_key`.
3. `merge`: status → source → also_seen_in → due date → notes.
4. Tests, including idempotency and order-independence of ingest.

## Risks
- Order of ingestion changes which occurrence is primary: solved by choosing earliest `source_date`, not file order.
- Unicode punctuation (curly quotes, en dashes) must normalise away, or duplicates will slip through.
- Unassigned items with the same task across *different people's* meetings merge. Accepted: they are unowned anyway.

## Definition of done
All `test-cases.md` pass; merge is idempotent and commutative on primary-source choice.
