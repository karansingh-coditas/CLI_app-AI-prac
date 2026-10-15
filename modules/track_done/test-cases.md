# track_done — Test Cases

| ID | Given | When | Then |
|---|---|---|---|
| TD-T1 | open item id 12 | `mark_done(12)` | **AC-9:** outcome `done`; status done; `done_at == now`; message echoes task |
| TD-T2 | item 12 marked done | `store.query(status="open")` / `track_list` | item no longer listed as open |
| TD-T3 | done item | `mark_done` again | `already_done`; `done_at` unchanged; exit mapping 0 |
| TD-T4 | no item 999 | `mark_done(999)` | `not_found`; message `No item with id 999`; store unchanged |
| TD-T5 | overdue item | `mark_done` | becomes done; `is_overdue` False afterwards |
| TD-T6 | item marked done, then `ingest` of a note still showing `[ ]` | ingest again | stays done (cross-check with `ingest_runner` IG-T11) |
| TD-T7 | item marked done | inspect source `.md` | file unchanged (FR-D4) |
| TD-T8 | item marked done, then included in `followup` | `followup_runner` | item excluded (cross-check with `followup_runner`) |
| TD-T9 | item with `also_seen_in` | `mark_done` | only that one row changes |
