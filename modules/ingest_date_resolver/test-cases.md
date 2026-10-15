# ingest_date_resolver — Test Cases

Reference meeting dates: **M1 = Mon 2026-10-12**, **M2 = Fri 2026-10-16**, **M3 = Sat 2026-10-17**.

| ID | Text | Meeting | Then |
|---|---|---|---|
| DR-T1 | `send the revised quote by Friday` | M1 | due 2026-10-16, text `send the revised quote` (**AC-3**) |
| DR-T2 | `send quote by Friday` | M2 (Friday) | due 2026-10-23 (strictly after) |
| DR-T3 | `send quote by Monday` | M1 | due 2026-10-19 |
| DR-T4 | `send quote by Sat` | M3 | due 2026-10-24 |
| DR-T5 | `fix bug by 2026-10-30` | M1 | due 2026-10-30, phrase removed |
| DR-T6 | `fix bug by 30 Oct` | M1 | due 2026-10-30 (meeting year) |
| DR-T7 | `fix bug by Oct 30, 2027` | M1 | due 2027-10-30 |
| DR-T8 | `fix bug due 30 October 2026` | M1 | due 2026-10-30 |
| DR-T9 | `call client today` | M1 | due 2026-10-12 |
| DR-T10 | `call client by tomorrow` | M2 | due 2026-10-17 |
| DR-T11 | `plan sprint by next week` | M1 | due 2026-10-19 (coming Monday) |
| DR-T12 | `plan sprint by next week` | M2 | due 2026-10-19 |
| DR-T13 | `finish report by end of week` | M1 | due 2026-10-16 |
| DR-T14 | `finish report by end of week` | M3 | due 2026-10-23 (Sat → following Friday) |
| DR-T15 | `finish report by end of month` | M1 | due 2026-10-31 |
| DR-T16 | `finish report by eom` | meeting 2028-02-10 | due 2028-02-29 (leap year) |
| DR-T17 | `finish report before 20 Oct` | M1 | due 2026-10-20 (stated date) |
| DR-T18 | `update the doc` | M1 | due None, text unchanged, no warning |
| DR-T19 | `fix bug by 31 Feb` | M1 | due None, text unchanged, warning with phrase |
| DR-T20 | `fix bug by Fiday` | M1 | due None, text unchanged, warning |
| DR-T21 | `book venue by soon` | M1 | due None; text unchanged |
| DR-T22 | `rotate pager, on call by hand` | M1 | due None; no crash; text unchanged |
| DR-T23 | `ship it BY FRIDAY` | M1 | due 2026-10-16 (case-insensitive) |
| DR-T24 | `ship it 2026-10-30` (trailing, no introducer) | M1 | due 2026-10-30 |
| DR-T25 | `fix by 2026-10-30 and review by Friday` | M1 | first introducer wins: due 2026-10-30 |
| DR-T26 | `by Friday` only (empty remainder) | M1 | due 2026-10-16; `task_text` is empty string, no crash |
| DR-T27 | any input | any | never raises; no `date.today()` use |
