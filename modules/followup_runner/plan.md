# followup_runner — Plan

## Approach
A linear function with early returns, one per outcome in the spec. Dependencies injected, so tests use `Store(":memory:")` + `FakeGateway`.

## Design decisions
- **Outcome object, not exceptions,** for expected cases (ambiguous, no items, no email). Only genuine failures (`AppError` from the gateway) propagate.
- **Depends on the gateway protocol only.** `cli_app` decides between `McpGmailGateway` and `DryRunGateway`, so `--dry-run` needs no logic here.
- **Selection uses `store.query(owner_key, status="open")`:** the store does the filtering. `compose` re-checks defensively.
- **Ambiguity is checked before anything else** so a wrongly-matched person can never be emailed (AC-11).
- **Unassigned count** is computed with one extra `store.query(owner_key="unassigned", status="open")`.

## Steps
1. Owner lookup branches (ambiguous / not_found / unassigned).
2. Item query and `compose`.
3. No-email policy and `--no-recipient`.
4. Gateway call and success message.
5. Unassigned note.
6. Tests with seeded store and `FakeGateway`.

## Risks
- The same real person may be stored twice (once with email from one note, once without from another). `Person.key` differs, so they appear as two owners and the lookup is ambiguous. User resolves by typing the email. Mitigation to consider later: add emails consistently in notes.
- Users expecting `followup` with no argument to cover everyone (Q-5). Currently exit 2 with usage help from `cli_app`.

## Definition of done
All `test-cases.md` pass, including a check that only `create_draft` is called.
