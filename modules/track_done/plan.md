# track_done — Plan

## Approach
A ~10-line function over `store.mark_done` / `store.get`. Kept as its own module so the command can be built, tested and changed (e.g. adding `undo` later) without touching `track_list`.

## Design decisions
- **Atomic decision lives in `core_store.mark_done`** (single UPDATE ... WHERE status='open'), so two concurrent calls cannot both report `done`.
- **Result object with a ready message** so `cli_app` only prints and maps the exit code.
- **Not-found is exit 2** (the user typed a bad id), consistent with the ambiguous-owner convention.

## Steps
1. Call `store.mark_done`.
2. Fetch the item for the message.
3. Build `DoneResult`.
4. Tests on an in-memory store.

## Risks
- Wrong id typed by the user marks a different real item. Mitigation: the message echoes the task text, so the mistake is visible.

## Definition of done
All `test-cases.md` pass.
