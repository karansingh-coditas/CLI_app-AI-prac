# cli_app — Plan

## Approach
`argparse` with subparsers. One small handler function per command, each building its collaborators and calling a module's public function. `main` returns an int; the console-script wrapper calls `sys.exit`.

## Design decisions
- **`argparse` (stdlib):** four commands do not justify `click`/`typer`.
- **`main` takes `env`, `stdout`, `stderr`** so tests run it in-process with no subprocess and no real environment.
- **Only wiring here:** if a handler grows logic beyond "build, call, print, map exit code", that logic belongs in the module it serves.
- **Gateway constructed lazily** (inside the `followup` handler), so `ingest`/`list`/`done` work with no Gmail setup or MCP library.
- **One catch point** for `AppError` and unexpected exceptions, producing uniform `error:` messages.
- **Argparse errors already exit 2;** wrap `SystemExit` from argparse into a return value so `main` is testable.

## Steps
1. Parser definition with help texts.
2. Global option resolution (`--db`, `--today`, `--verbose`).
3. Handlers: `ingest`, `list`, `done`, `followup`.
4. Central error handling and exit codes.
5. `pyproject.toml` console script and Python ≥ 3.10 constraint.
6. End-to-end tests invoking `main([...])` against fixture notes with `FakeGateway` patched in.

## Risks
- Hidden coupling creeping in: keep handlers ≤ ~15 lines each.
- Windows console encoding for `—` and `…`: set stdout reconfigure to UTF-8 where possible; fall back to ASCII replacements if the stream can't encode.
- Date parsing for `--due-before` / `--today` duplicates `resolve_today` format: share one `parse_iso_date` helper (private to this file).

## Definition of done
All `test-cases.md` pass; `actiontrack --help` and every subcommand `--help` work after `pip install -e .`.
