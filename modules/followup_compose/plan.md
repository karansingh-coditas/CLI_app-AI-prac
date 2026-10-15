# followup_compose — Plan

## Approach
Filter → sort → partition by `is_overdue` → render with f-strings. Pure function, snapshot-style tests on the exact text.

## Design decisions
- **Returns `None` for nothing to do**, so the runner has one clear "nothing to follow up" branch (FR-F6).
- **Re-filters defensively** (open + same owner), so a caller bug can never put someone else's tasks in an email.
- **Plain text, f-strings:** no templating engine for a single fixed layout.
- **Overdue partition uses `core_models.is_overdue`** (same definition as `list`).
- Day counts computed from `today` (parameter), keeping tests deterministic.

## Steps
1. Selection + de-dup + ordering.
2. Line renderer (due text, overdue days, source).
3. Body/subject assembly and `Draft` creation.
4. Snapshot tests.

## Risks
- Tasks containing newlines or odd characters: collapse internal whitespace when rendering one line per task.
- Very long lists make long emails; accepted in v1.

## Definition of done
All `test-cases.md` pass; imports only `core_models`.
