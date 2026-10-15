# track_owner_lookup — Tasks

- [ ] OL-1 Define `LookupResult`
- [ ] OL-2 Implement `unassigned` keyword handling
- [ ] OL-3 Implement exact email match
- [ ] OL-4 Implement exact full-name match (with same-name-different-email → ambiguous)
- [ ] OL-5 Implement first-name match (unique → found, multiple → ambiguous)
- [ ] OL-6 Stable candidate ordering; blank query → `not_found`
- [ ] OL-7 Write `tests/test_track_owner_lookup.py` for all cases in `test-cases.md`
