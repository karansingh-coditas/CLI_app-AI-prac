# track_list — Plan

## Approach
Push the cheap filters (owner, done/open, due-before) into `store.query`, apply the derived `overdue` filter and ordering in Python using `core_models.is_overdue`. Render with plain string formatting.

## Design decisions
- **Overdue is derived, never stored.** A single definition (`is_overdue`) is used here and by `followup_compose`, so the two cannot diverge.
- **`today` is a parameter,** not read from the clock, making overdue tests deterministic.
- **Result object instead of exceptions** for ambiguous/not-found owners: these are normal outcomes the CLI turns into exit code 2.
- **No table library:** fixed columns with width computed from data (`str.ljust`) is enough.

## Steps
1. Owner lookup integration (`found` / `unassigned` / `ambiguous` / `not_found`).
2. Filter composition and the overdue filter.
3. Sort key: `(not overdue, due_date is None, due_date, id)`.
4. `format_table`.
5. Tests with a seeded in-memory store.

## Risks
- `open` including overdue could surprise users: stated in `--help` text (owned by `cli_app`).
- Wide unicode in names misaligns columns; acceptable for v1.

## Definition of done
All `test-cases.md` pass.
