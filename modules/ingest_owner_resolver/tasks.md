# ingest_owner_resolver — Tasks

- [ ] OR-1 Define `OwnerResult` dataclass
- [ ] OR-2 Implement prefix regex (`<1–3 name words> to|will <rest>`), allow `.`, `-`, `'`, non-ASCII letters
- [ ] OR-3 Implement matching ladder: full name → first name + initial → first name
- [ ] OR-4 Return `resolved` / `ambiguous` / `unknown` / `none` with correct `task_text` and `note`
- [ ] OR-5 Handle full-name collision across different emails as `ambiguous`
- [ ] OR-6 Write `tests/test_ingest_owner_resolver.py` for all cases in `test-cases.md`
