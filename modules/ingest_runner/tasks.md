# ingest_runner — Tasks

- [ ] IRN-1 Define `IngestReport`
- [ ] IRN-2 Folder validation (`AppError` exit 1) and non-recursive sorted `*.md` listing
- [ ] IRN-3 Read + UTF-8/BOM decode with error → skipped `Issue`
- [ ] IRN-4 Call `parse_note`; on `MalformedNote` skip file and store nothing
- [ ] IRN-5 Per-line pipeline: `resolve_owner` → `resolve_due` → empty-task fallback → build `Item` (status from `checked`)
- [ ] IRN-6 Persist: `find_by_key` → `add` or `merge` + `update`; collect `Issue`s from merge
- [ ] IRN-7 Wrap each file in `store.atomic()`; convert unexpected exceptions to `Issue` and continue
- [ ] IRN-8 Counters (added / merged / updated / unassigned / ambiguous / no-due) per spec rules
- [ ] IRN-9 `format_report` text per spec
- [ ] IRN-10 Confirm notes are opened read-only (no write calls on source paths)
- [ ] IRN-11 Build fixtures: 3 valid notes with a repeated item, 1 same-first-name note, 1 malformed note
- [ ] IRN-12 Write `tests/test_ingest_runner.py` for all cases in `test-cases.md`, including the 500-note timing test
