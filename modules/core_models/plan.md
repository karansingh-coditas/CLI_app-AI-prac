# core_models — Plan

## Approach
Plain `dataclasses`, no behaviour beyond two small pure functions. Build first; everything else depends on it.

## Design decisions
- `Person` equality on `.key` only, so `Person("Priya Sharma", "P@x.com") == Person("Priya Sharma", "p@x.com")`.
- `Item` is mutable (merge and mark-done edit fields). All other types are frozen.
- `dedup_key` lives on `Item` so `core_store` can index it without importing `ingest_dedup`.
- `Issue` (not `Warning`) to avoid shadowing the builtin.
- Dates are `datetime.date`. No timezones (NFR-10).

## Steps
1. Create dataclasses and exceptions.
2. Implement `norm_name`, `Person.key/first_name`.
3. Implement `is_overdue`, `resolve_today`.
4. Unit tests.

## Risks
- Contract churn: any later change to `Item` ripples to all modules. Mitigation: freeze this spec before step 3 of the build order.

## Definition of done
All tests in `test-cases.md` pass; no import outside stdlib.
