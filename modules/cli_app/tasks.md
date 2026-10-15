# cli_app — Tasks

- [ ] CA-1 Create `pyproject.toml` (Python ≥ 3.10, dependency PyYAML, console script `actiontrack`)
- [ ] CA-2 Build `argparse` parser: global options + `ingest`, `list`, `done`, `followup` with help text
- [ ] CA-3 Resolve `today` once (`resolve_today`) and DB path (`default_db_path`)
- [ ] CA-4 `ingest` handler: report to stdout, warnings/skips to stderr
- [ ] CA-5 `list` handler: ambiguous/not-found → stderr + exit 2; table to stdout
- [ ] CA-6 `done` handler with exit-code mapping
- [ ] CA-7 `followup` handler: lazy gateway (`DryRunGateway` vs `McpGmailGateway`), print outcome, exit code
- [ ] CA-8 Central error handling: `AppError`, unexpected exceptions, `--verbose` tracebacks
- [ ] CA-9 Wrap argparse `SystemExit` so `main` returns the code
- [ ] CA-10 UTF-8 / encoding-safe output on Windows
- [ ] CA-11 Write `tests/test_cli_app.py` end-to-end cases from `test-cases.md` using fixture notes and `FakeGateway`
