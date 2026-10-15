# cli_app — Test Cases

All tests call `main([...], env=…, stdout=…, stderr=…)` in-process with a temp DB and fixture notes. Gmail is `FakeGateway` (passed as `gateway_factory`) or `--dry-run`.

| ID | Command | Then |
|---|---|---|
| CA-T1 | `ingest <fixtures>` | exit 0; stdout summary with counts; skipped malformed note named on stderr |
| CA-T2 | `ingest` then `list` | table has `ID OWNER TASK DUE STATUS SOURCE`; items from fixtures |
| CA-T3 | `ingest` twice | second summary shows 0 added; `list` row count unchanged (**AC-12**) |
| CA-T4 | `--today 2026-10-15 list --status overdue` | only overdue rows (**AC-7**) |
| CA-T5 | `list --owner Rahul --due-before 2026-10-25` | AND filter result (**AC-8**) |
| CA-T6 | `list --owner Priya` with two Priyas | exit 2; candidates on stderr |
| CA-T7 | `list --status bogus` | exit 2; argparse usage on stderr |
| CA-T8 | `list --due-before 12/10/2026` | exit 2; clear date-format message |
| CA-T9 | `list` on empty DB | stdout `No items match`; exit 0 |
| CA-T10 | `done 1` | exit 0; message; `list --status done` shows it (**AC-9**) |
| CA-T11 | `done 1` again | exit 0; `already done` message |
| CA-T12 | `done 999` | exit 2; `No item with id 999` |
| CA-T13 | `done abc` | exit 2; usage error |
| CA-T14 | `followup Rahul --dry-run` | exit 0; draft text on stdout; no gateway call |
| CA-T15 | `followup Rahul` (fake gateway injected) | exit 0; draft id on stdout; exactly one draft (**AC-10**) |
| CA-T16 | `followup Priya` | exit 2; candidates; no draft (**AC-11**) |
| CA-T17 | `followup` (no owner) | exit 2; usage error |
| CA-T18 | gateway raises `AppError("Gmail connector unavailable…")` | stderr `error: …`; exit 1; no traceback |
| CA-T19 | induce unexpected exception | stderr `unexpected failure (<Type>); re-run with --verbose`; exit 1; no traceback |
| CA-T20 | same with `--verbose` | traceback shown |
| CA-T21 | `ingest <missing folder>` | exit 1; `error:` message |
| CA-T22 | `--db`, env `ACTIONTRACK_DB`, default | precedence honoured in that order |
| CA-T23 | `--today` vs env `ACTIONTRACK_TODAY` | `--today` wins; invalid value → exit 2 |
| CA-T24 | `--help` on top-level and each command | exit 0; `list --help` says `open` includes overdue |
| CA-T25 | `ingest`, `list`, `done` with MCP library uninstalled | all work (lazy gateway) |
| CA-T26 | task text with `—`/`…` on a cp1252 stream | no `UnicodeEncodeError` |
| CA-T27 | store closed after each command, including on error | temp DB file deletable on Windows |
