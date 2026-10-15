# followup_runner — Tasks

- [ ] FUR-1 Define `FollowupOutcome`
- [ ] FUR-2 Owner lookup branches with messages and exit 2 (ambiguous lists candidates; not found; unassigned)
- [ ] FUR-3 Query open items for the owner and call `compose`; handle `None` → "Nothing to follow up" exit 0
- [ ] FUR-4 No-email policy: exit 1 unless `no_recipient`
- [ ] FUR-5 Call `gateway.create_draft`; let `AppError` propagate
- [ ] FUR-6 Success message (draft id/link + included items)
- [ ] FUR-7 Unassigned-open-items note
- [ ] FUR-8 Verify store is only read and gateway only gets `create_draft`
- [ ] FUR-9 Write `tests/test_followup_runner.py` for all cases in `test-cases.md`
