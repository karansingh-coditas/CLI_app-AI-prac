# track_owner_lookup — Plan

## Approach
Linear scan over a short list (tens of people), three equality passes. No indexing needed.

## Design decisions
- **Separate module** because both `track_list` and `followup_runner` need identical behaviour (FR-E15). One implementation prevents the two commands from disagreeing about who "Priya" is.
- **Pure over a list** (not over the store), so it has no dependency on `core_store` and tests need no DB.
- **Strict equality only.** A typo must not select the wrong person: for a command that drafts emails to a named recipient, a wrong match is worse than a refusal.
- `unassigned` is handled here so `track_list` doesn't special-case it.

## Steps
1. Normalise query and compare by pass: unassigned → email → full name → first name.
2. Return `LookupResult` with sorted candidates.
3. Table-driven tests.

## Risks
- A real person whose name is "Unassigned": negligible; documented.
- Same person stored twice under different spellings (no email): shows up as two candidates. User disambiguates by typing the full name. Accepted for v1.

## Definition of done
All `test-cases.md` pass; imports only `core_models`.
