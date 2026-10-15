# track_owner_lookup — Spec

**Family:** `track_` · **File:** `src/actiontrack/track_owner_lookup.py` · **Depends on:** `core_models` only

## Purpose
Turn a user-typed owner string (from `list --owner` or `followup <owner>`) into exactly one stored `Person`, or explain why not. Pure function over a list of known owners.

## Requirements covered
FR-E15, FR-L2 (owner filter), FR-E7 (`unassigned` keyword), AC-11 (ambiguity handling).

## Public interface

```python
@dataclass(frozen=True)
class LookupResult:
    status: Literal["found", "ambiguous", "not_found", "unassigned"]
    person: Person | None = None
    candidates: tuple[Person, ...] = ()

def lookup_owner(query: str, owners: Sequence[Person]) -> LookupResult
```

## Rules
Case-insensitive, whitespace-trimmed. Checked in this order, first rule that yields a match wins:
1. Query equals `unassigned` or `(unassigned)` → `status="unassigned"`.
2. **Email** exact match (`Person.email`) → `found`. (Emails are unique per person.)
3. **Full name** exact match (normalised via `norm_name`):
   - one person → `found`;
   - several people with the same full name (different emails) → `ambiguous`.
4. **First name** match (`Person.first_name`):
   - one person → `found`;
   - several → `ambiguous` with all candidates;
5. Nothing matched → `not_found`.

Additional rules:
- Empty/blank query → `not_found`.
- `candidates` is sorted by name then email for stable output.
- The function never picks one of several candidates on its own, and never partial-matches (no substring/fuzzy).
- Never raises.

## Caller contract
`ambiguous` → caller prints each candidate as `Name <email>` and exits with code 2 without acting. `not_found` → caller prints an error and exits 2 (usage error).

## Out of scope
Querying the DB (callers pass `store.owners()`), output formatting, exit codes.
