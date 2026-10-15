# followup_compose — Spec

**Family:** `followup_` · **File:** `src/actiontrack/followup_compose.py` · **Depends on:** `core_models` only

## Purpose
Build the follow-up email (`Draft`) for one owner from their items. Pure: no Gmail, no DB, no clock.

## Requirements covered
FR-F1, FR-F2, FR-E4, FR-E8 (no due date wording), IR-3 (subject/body shape).

## Public interface

```python
def compose(owner: Person, items: Sequence[Item], today: date) -> Draft | None
```

`None` when there is nothing to follow up (no open items after filtering).

## Rules
1. **Selection:** keep items where `status == "open"` and `owner` equals `owner` (by `Person.key`). Done items and other people's items are dropped defensively, even if passed in.
2. **De-duplication:** items with the same `id` appear once.
3. **Sections:** `Overdue` (where `is_overdue(item, today)`), then `Open`. A section with no items is omitted. Within a section: due date ascending, undated last, then `id`.
4. **Each line:** `- <task> — due <Fri 16 Oct 2026> (from <source file stem>, <meeting date>)`. Undated → `— no due date`. Overdue lines add `(<N> days overdue)`.
5. **Greeting / closing:** `Hi <first name>,` + one-sentence intro + `Thanks,` (no sender name is invented).
6. **Subject:** `Action items follow-up — <first name> — <YYYY-MM-DD of today>`.
7. **`to`:** `owner.email`, or `None` if unknown. This module only reports; the caller decides what to do (FR-F7).
8. **`included_ids`:** ids in the order they appear in the body.
9. Plain text only. Task text is included as-is (no HTML).
10. Never raises for a valid owner and items.

## Out of scope
Deciding whether to create a draft, sending, localisation, HTML templates, signatures.
