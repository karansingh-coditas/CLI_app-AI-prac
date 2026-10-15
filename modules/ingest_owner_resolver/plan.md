# ingest_owner_resolver — Plan

## Approach
One compiled regex for the prefix, then a three-step attendee match. Pure function, table-driven tests.

## Design decisions
- **Anchored prefix pattern** keeps false positives low. "Update the onboarding doc" has no `to`/`will` after the leading words, so `none`.
- **On `ambiguous` / `unknown`, the full original text is kept as task text.** Stripping the name would lose information the human needs to fix it.
- **Resolution scope is the note's own attendees**, so same-first-name collisions can only arise inside one meeting. The common case (one Priya per meeting) resolves cleanly.
- The `Person` returned is the attendee object, so email and key flow through unchanged.

## Steps
1. Prefix regex and name tokeniser.
2. Matching ladder (full name → first + initial → first name).
3. Result construction and notes text.
4. Tests (table-driven).

## Risks
- False positive: "Update to docs" parses `Update` as a name → resolves to `unknown` (kept as unassigned with a warning). Acceptable; the item is never lost.
- Names with hyphens or apostrophes (`Mary-Jane`, `O'Neil`): allow `-` and `'` inside a word.
- Non-ASCII names: use `str.isalpha()` rather than `[A-Za-z]`.

## Definition of done
All `test-cases.md` pass; module has no imports beyond `core_models` and stdlib `re`.
