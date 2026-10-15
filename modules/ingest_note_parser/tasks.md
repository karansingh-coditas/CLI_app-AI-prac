# ingest_note_parser — Tasks

- [ ] NP-1 Add PyYAML to `pyproject.toml` dependencies
- [ ] NP-2 Implement front-matter splitter (opening/closing `---`, CRLF and BOM safe)
- [ ] NP-3 Implement YAML load with `safe_load`; map errors to `MalformedNote`
- [ ] NP-4 Validate `date` (date object or ISO string)
- [ ] NP-5 Parse `attendees` into `Person` (name + optional email), collapse duplicates by key
- [ ] NP-6 Implement body item regex (`- [ ]`, `- [x]`, `* [ ]`) with original line numbers
- [ ] NP-7 Enforce "only `MalformedNote` escapes" (wrap unexpected errors)
- [ ] NP-8 Create fixtures `tests/fixtures/notes/` (valid, no-front-matter, bad-yaml, bad-date, no-attendees, empty, no-items)
- [ ] NP-9 Write `tests/test_ingest_note_parser.py` for all cases in `test-cases.md`
