# track_list — Test Cases

Seed (today = 2026-10-15): 
#1 Priya Sharma, open, due 10-10 · #2 Priya Sharma, open, due 10-15 · #3 Rahul, open, due 10-20 · #4 Rahul, done, due 10-01 · #5 unassigned, open, no due · #6 Priya Nair, open, due 10-12 · #7 Rahul, open, no due.

| ID | Call | Then |
|---|---|---|
| TL-T1 | no filters | all 7 items, in order #1, #6 (overdue, due asc), #4, #2, #3 (non-overdue, due asc), #5, #7 (undated, by id) |
| TL-T2 | `status=overdue` | **AC-7:** #1, #6 only |
| TL-T3 | `status=open` | #1, #2, #3, #5, #6, #7 (overdue included) |
| TL-T4 | `status=done` | #4 only |
| TL-T5 | `due_before=2026-10-16` | #1, #2, #4, #6 (undated excluded) |
| TL-T6 | `owner="Rahul", due_before=2026-10-25` | **AC-8:** #3, #4 (AND of both) |
| TL-T7 | `owner="Priya"` | `ambiguous_owner`, candidates Priya Nair & Priya Sharma, no items |
| TL-T8 | `owner="Priya Sharma"` | #1, #2 |
| TL-T9 | `owner="ps@x.com"` (email) | #1, #2 |
| TL-T10 | `owner="Anita"` | `owner_not_found` |
| TL-T11 | `owner="unassigned"` | #5 only |
| TL-T12 | `owner=Rahul, status=overdue` | empty (none overdue) → `No items match` |
| TL-T13 | item due == today (#2) | not overdue; displayed `open` |
| TL-T14 | undated item (#5, #7) | never displayed `overdue`; due shown `—` |
| TL-T15 | unassigned item row | owner column `(unassigned)` |
| TL-T16 | overdue open item row | status column `overdue` |
| TL-T17 | merged item with 2 extra sources | source column ends ` (+2)` |
| TL-T18 | task of 100 chars | truncated to 60 with `…` |
| TL-T19 | empty store | `No items match`, no error |
| TL-T20 | ordering | overdue → due asc → undated; done items sort by the same key (never overdue); ties by id |
| TL-T21 | duplicates in source notes ingested earlier | each logical item appears once (FR-E4) |
