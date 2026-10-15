# core_models — Tasks

- [ ] CM-1 Create `src/actiontrack/core_models.py` with `Person`, `RawItemLine`, `Note`, `Item`, `Issue`, `Draft`, `DraftResult`
- [ ] CM-2 Add `MalformedNote`, `AppError` exceptions and exit-code constants
- [ ] CM-3 Implement `norm_name`, `Person.key`, `Person.first_name`, key-based `__eq__`/`__hash__`
- [ ] CM-4 Implement `is_overdue(item, today)`
- [ ] CM-5 Implement `resolve_today(cli_value, env)` with precedence and validation
- [ ] CM-6 Write `tests/test_core_models.py` covering all cases in `test-cases.md`
- [ ] CM-7 Confirm module imports nothing outside stdlib
