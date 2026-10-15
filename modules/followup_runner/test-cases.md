# followup_runner — Test Cases

Seed (today 2026-10-15): Rahul (`rahul@x.com`): #1 overdue, #2 open, #3 done. Priya Sharma (`ps@x.com`) and Priya Nair (`pn@x.com`) each with open items. Dev Patel (no email) with an open item. One unassigned open item. `FakeGateway`.

| ID | Call | Then |
|---|---|---|
| FU-T1 | `run_followup("Rahul")` | **AC-10:** exit 0; one draft to `rahul@x.com`; body has Overdue (#1) and Open (#2); #3 absent; message shows draft id and items |
| FU-T2 | `run_followup("Priya")` | **AC-11:** exit 2; message lists both Priyas as `Name <email>`; `FakeGateway.drafts == []` |
| FU-T3 | `run_followup("Priya Nair")` | exit 0; draft only has Nair's items |
| FU-T4 | `run_followup("pn@x.com")` | exit 0; same as FU-T3 |
| FU-T5 | `run_followup("Anita")` | exit 2, `No owner matches 'Anita'`; no draft |
| FU-T6 | `run_followup("unassigned")` | exit 2 with explanation; no draft |
| FU-T7 | owner whose items are all done | exit 0, `Nothing to follow up for …`; no draft |
| FU-T8 | `run_followup("Dev")` (no email) | exit 1, message mentions `--no-recipient`; no draft |
| FU-T9 | `run_followup("Dev", no_recipient=True)` | exit 0; draft created with `to=None` |
| FU-T10 | gateway raises `AppError` (connector down) | error propagates (caller exits 1); store unchanged; re-run works |
| FU-T11 | run twice for Rahul | two drafts created (FR-F9) |
| FU-T12 | success with unassigned open items present | message ends with `1 unassigned open item(s) not included (no recipient)` |
| FU-T13 | item marked done after first run | next run excludes it (cross-check `track_done`) |
| FU-T14 | spy gateway | only `create_draft` ever called; no other attribute used |
| FU-T15 | store snapshot before/after | unchanged (read-only) |
| FU-T16 | `DryRunGateway` supplied | same flow; draft text printed; no Gmail call; exit 0 |
