# ingest_date_resolver — Tasks

- [ ] DR-1 Define `DueResult`
- [ ] DR-2 Phrase locator: introducers `by|before|on|due|until` + trailing-expression fallback
- [ ] DR-3 Matcher: ISO date
- [ ] DR-4 Matchers: written dates with/without year (`30 Oct`, `Oct 30, 2026`)
- [ ] DR-5 Matcher: weekday names (strictly after meeting date; same weekday → +7)
- [ ] DR-6 Matchers: `today`, `tomorrow`, `next week`, `end of week`/`eow`, `end of month`/`eom`
- [ ] DR-7 Clean task text after removing the phrase
- [ ] DR-8 Unresolvable phrase → `due=None`, text unchanged, warning (only when phrase looks date-like)
- [ ] DR-9 Ensure no use of `date.today()`
- [ ] DR-10 Write `tests/test_ingest_date_resolver.py` for all cases in `test-cases.md`
