# ingest_runner — Test Cases

Uses real parser/resolvers/dedup, `Store(":memory:")` and a fixed `now`.

| ID | Given | When | Then |
|---|---|---|---|
| IG-T1 | folder with 3 valid notes | `run_ingest` | **AC-1:** items stored with owner, task, due date, source; report counts match |
| IG-T2 | same item in note A (10-05) and note B (10-12) | ingest | **AC-2:** one row; `also_seen_in` lists B; `items_merged == 1` |
| IG-T3 | item with no owner pattern | ingest | **AC-4:** stored, owner NULL; counted in `items_unassigned` |
| IG-T4 | item with no due phrase | ingest | stored, `due_date` NULL; counted in `items_no_due` |
| IG-T5 | note with two Priyas, text `Priya to send quote` | ingest | **AC-5:** unassigned, `notes` contains ambiguity text; `items_ambiguous == 1`; warning in report |
| IG-T6 | Priya Sharma and Priya Nair each own a same-text item | ingest | two rows, different owners (not merged) |
| IG-T7 | folder includes note with no front matter | ingest | **AC-6:** file in `files_skipped` with reason; other notes ingested; no exception; no rows from it |
| IG-T8 | note with bad date + valid note | ingest | bad one skipped, valid one stored |
| IG-T9 | non-UTF-8 file bytes | ingest | skipped as malformed, run continues |
| IG-T10 | run twice on the same folder | ingest ×2 | **AC-12:** second run `added=0, merged=0, updated=0`; row count unchanged |
| IG-T11 | item marked done via `store.mark_done`, then re-ingest where note still shows `[ ]` | re-ingest | stays `done` |
| IG-T12 | note shows `[x]` for a known open item | re-ingest | item becomes `done`; counted updated |
| IG-T13 | `- [x]` item in a new note | ingest | stored with status done |
| IG-T14 | later note changes due date Friday → next Friday | re-ingest | latest due kept; `DUE_CHANGED` in issues |
| IG-T15 | folder missing | `run_ingest` | `AppError`, `exit_code == 1` |
| IG-T16 | path is a file, not a folder | `run_ingest` | `AppError`, exit 1 |
| IG-T17 | folder with `.md` and `.txt` and a subfolder with `.md` | ingest | only top-level `.md` read (FR-N4) |
| IG-T18 | empty folder | ingest | report with 0 files; exit-normal; no error |
| IG-T19 | pipeline raises unexpectedly on file 2 (inject fault) | ingest | file 2 rolled back, issue recorded, file 3 still ingested |
| IG-T20 | item line `- [ ] by Friday` (task empty after stripping) | ingest | stored with raw text as task; `UNPARSEABLE_ITEM` warning |
| IG-T21 | items in the same note repeated twice | ingest | one row (same-file repeat merged) |
| IG-T22 | source files checksum before/after | ingest | files unchanged (NFR-5) |
| IG-T23 | ingestion order reversed (rename files) | ingest | same final rows and same primary sources |
| IG-T24 | 500 generated notes × 10 items | ingest | finishes in < 10 s (NFR-4) |
| IG-T25 | `format_report` on a populated report | format | contains counts, skipped files with reasons, warnings with file:line |
