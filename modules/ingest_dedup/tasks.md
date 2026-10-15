# ingest_dedup — Tasks

- [ ] DD-1 Implement `normalise_task` (lower-case, strip ASCII + Unicode punctuation, collapse whitespace)
- [ ] DD-2 Implement `dedup_key(owner, task)` using `Person.key` or `-`
- [ ] DD-3 Define `MergeResult`
- [ ] DD-4 `merge`: status rule (done wins, never reopen, `done_at` handling)
- [ ] DD-5 `merge`: primary source = earliest `source_date`; maintain `also_seen_in` without duplicates or the primary
- [ ] DD-6 `merge`: due-date rule (keep later) and `DUE_CHANGED` issue
- [ ] DD-7 `merge`: union `notes`; keep existing task/owner/raw_text
- [ ] DD-8 Guarantee no mutation of inputs and `changed=False` on identical re-ingest
- [ ] DD-9 Write `tests/test_ingest_dedup.py` for all cases in `test-cases.md`
