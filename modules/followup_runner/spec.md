# followup_runner — Spec

**Family:** `followup_` · **File:** `src/actiontrack/followup_runner.py`
**Depends on:** `core_models`, `core_store`, `track_owner_lookup`, `followup_compose`, and the `DraftGateway` **protocol** (injected; the module never imports a concrete Gmail class).

## Purpose
Orchestrate `actiontrack followup <owner>`: resolve the owner, gather their open items, compose the email, create a draft, and report. Contains no wording rules and no Gmail code.

## Requirements covered
FR-F1 (selection via store), FR-F5, FR-F6, FR-F7, FR-F9, FR-E7 (unassigned count), FR-E15. Acceptance: AC-10, AC-11.

## Public interface

```python
@dataclass
class FollowupOutcome:
    exit_code: int
    message: str                              # full text for stdout
    candidates: tuple[Person, ...] = ()       # when ambiguous
    draft_result: DraftResult | None = None
    included_ids: tuple[int, ...] = ()

def run_followup(owner_query: str, store: Store, gateway: DraftGateway,
                 today: date, no_recipient: bool = False) -> FollowupOutcome
```

## Flow and outcomes

1. `lookup_owner(owner_query, store.owners())`:
   - `ambiguous` → exit **2**, message lists `Name <email>` per candidate and says to retype with full name or email. No draft.
   - `not_found` → exit **2**, `No owner matches '<query>'`. No draft.
   - `unassigned` → exit **2**, `Unassigned items have no recipient; assign an owner in the notes`. No draft.
   - `found` → continue.
2. `items = store.query(owner_key=person.key, status="open")`.
3. `draft = compose(person, items, today)`. `None` → exit **0**, `Nothing to follow up for <name>`. No draft (FR-F6).
4. `draft.to is None` and not `no_recipient` → exit **1**, `<name> has no email address in any note; use --no-recipient to create a draft anyway`. No draft (FR-F7).
5. `gateway.create_draft(draft)`. `AppError` propagates (exit 1, FR-F8 handled by `cli_app`).
6. Success → exit **0**, message: draft id/link, list of included items (id, task, due), and — when unassigned open items exist — `N unassigned open item(s) not included (no recipient)` (FR-E7).
7. Every run creates a **new** draft; no draft de-duplication (FR-F9).
8. **No send:** the module only ever calls `gateway.create_draft`.
9. Store is read-only here (nothing is marked, nothing changes).

## Exit-code summary
0 draft created / nothing to follow up · 1 runtime error (no email, Gmail failure) · 2 usage (ambiguous, not found, unassigned).

## Out of scope
Email wording, Gmail transport, `--all` owners (Q-5), dry-run rendering (provided by choosing `DryRunGateway`).
