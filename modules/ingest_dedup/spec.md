# ingest_dedup — Spec

**Family:** `ingest_` · **File:** `src/actiontrack/ingest_dedup.py` · **Depends on:** `core_models` only

## Purpose
Define what "the same action item" means and how two occurrences merge. Pure functions. It does not read or write the database.

## Requirements covered
FR-E1, FR-E2, FR-E3, FR-E5, FR-I3 (no duplicate/reset), FR-I7, Q-4, Q-9.

## Public interface

```python
def normalise_task(task: str) -> str
def dedup_key(owner: Person | None, task: str) -> str

@dataclass(frozen=True)
class MergeResult:
    item: Item                 # merged result (existing object mutated copy, same id)
    changed: bool              # anything differs from `existing`
    issues: tuple[Issue, ...]  # e.g. DUE_CHANGED

def merge(existing: Item, incoming: Item) -> MergeResult
```

## Rules

**Normalisation** (`normalise_task`): lower-case → remove all punctuation → collapse whitespace → strip. The caller passes the task text *after* owner prefix and due phrase were removed.

**Key** (`dedup_key`): `"<owner.key or '-'>|<normalise_task(task)>"`. Two items match only on exact key equality (no fuzzy matching, FR-E5). Unassigned items with the same normalised task share the key `-|…`. Two people with the same first name have different keys (FR-E13).

**Merge** (`incoming` has the same key as `existing`; the id is kept from `existing`):
1. **Status:** `done` wins. If either is done → `done`. A `done` item is never reopened (Q-4). If `incoming` is done and `existing` is open, take `done_at` from `incoming` (the runner sets it to its `now` for checked lines). An existing `done_at` is never overwritten.
2. **Primary source:** the occurrence with the **earliest** `source_date` becomes `source_file`/`source_date`. On a tie, `existing` stays. The other source goes to `also_seen_in`.
3. **`also_seen_in`:** add the non-primary `source_file` when absent. Never contains the primary or duplicates. Same file twice (repeat inside one note) adds nothing.
4. **Due date:** if both are set, keep the **later**. If only one is set, keep it. If the kept value differs from `existing.due_date` and `existing.due_date` was set, emit `Issue(code="DUE_CHANGED")`.
5. **Task text / owner / raw_text:** keep `existing`'s.
6. **Notes:** union of both `notes` lists, order preserved, no repeats.
7. **Idempotency:** `merge(existing, incoming)` where `incoming` is the same item from the same file returns `changed=False`.
8. Does not mutate its arguments.

## Out of scope
Fuzzy/near-duplicate matching, persistence, counting (the runner counts merges).
