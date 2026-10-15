# cli_app — Spec

**Family:** `cli_` · **File:** `src/actiontrack/cli_app.py` · **Depends on:** all runner modules, `core_models`, `core_store`, `followup_gmail_draft` (wiring only)

## Purpose
The only entry point and the only place where concrete classes are wired together: argument parsing, building collaborators, printing, exit codes, error presentation.

## Requirements covered
§6 command surface, FR-E19, FR-F10 (`--dry-run` wiring), NFR-7, NFR-8, NFR-1 (console script). Smoke-level coverage of all ACs.

## Public interface

```python
def main(argv: Sequence[str] | None = None, env: Mapping[str, str] = os.environ,
         stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr,
         gateway_factory: Callable[[], DraftGateway] = McpGmailGateway) -> int
```
`gateway_factory` is the test seam: tests pass `FakeGateway`. It is called only by `followup` without `--dry-run`.
Console script: `actiontrack = actiontrack.cli_app:main` (wrapper calls `sys.exit(main())`).

## Commands

```
actiontrack [--db PATH] [--today YYYY-MM-DD] [--verbose] <command>

  ingest <folder>
  list   [--owner NAME] [--status open|done|overdue] [--due-before YYYY-MM-DD]
  done   <id>
  followup <owner> [--no-recipient] [--dry-run]
```

## Rules
1. **Global options:** `--db` (else env `ACTIONTRACK_DB`, else `./actiontrack.db`) · `--today` (else env `ACTIONTRACK_TODAY`, else system date) · `--verbose`.
2. **Wiring per command:**
   - `ingest` → `Store` + `run_ingest(folder, store, now)` → print `format_report` to stdout; skipped/warning lines also to stderr.
   - `list` → `list_items` → on `ambiguous_owner` print candidates to stderr, exit 2; on `owner_not_found` exit 2; else print `format_table`.
   - `done` → `mark_done`; print message; exit per `track_done` mapping.
   - `followup` → gateway = `DryRunGateway(stdout)` if `--dry-run` else `gateway_factory()` (constructed only now) → `run_followup`; print message.
3. **Argument validation → exit 2:** bad `--status` value, bad date format, non-integer `<id>`, missing `<owner>`/`<folder>`. `argparse` usage text goes to stderr.
4. **Exit codes (NFR-7):** 0 success · 1 runtime error (`AppError` with code 1, fatal IO) · 2 usage/ambiguous input.
5. **Errors:** `AppError` → `error: <message>` on stderr, exit its code. Any other exception → `error: unexpected failure (<type>); re-run with --verbose` and exit 1. **No traceback** unless `--verbose` (FR-E19).
6. Every command has `--help`. `list --help` states that `--status open` includes overdue items.
7. `today` is resolved once per invocation via `resolve_today` and passed down; `now` is `datetime.now()` (only for timestamps).
8. Output is plain text; stdout for results, stderr for warnings/errors.
9. The store is closed on exit, including on errors.

## Out of scope
Business logic of any command, config files, shell completion, colours.
