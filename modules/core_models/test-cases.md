# core_models — Test Cases

| ID | Given | When | Then |
|---|---|---|---|
| CM-T1 | `Person("Priya Sharma","A@X.com")` and `Person("Priya Sharma","a@x.com")` | compare | equal, same hash |
| CM-T2 | `Person("Priya Sharma","ps@x.com")`, `Person("Priya Nair","pn@x.com")` | compare, `first_name` | not equal; both `first_name == "Priya"` |
| CM-T3 | `Person("  Priya   Sharma ", None)` | `.key` | `"priya sharma"` |
| CM-T4 | open item, due 2026-10-10, today 2026-10-15 | `is_overdue` | True |
| CM-T5 | open item, due == today | `is_overdue` | False |
| CM-T6 | open item, due None | `is_overdue` | False |
| CM-T7 | done item, due in the past | `is_overdue` | False |
| CM-T8 | `--today 2026-01-05`, env set to another date | `resolve_today` | 2026-01-05 (CLI wins) |
| CM-T9 | no CLI value, env `ACTIONTRACK_TODAY=2026-02-03` | `resolve_today` | 2026-02-03 |
| CM-T10 | neither set | `resolve_today` | `date.today()` |
| CM-T11 | `--today not-a-date` | `resolve_today` | `AppError` with `exit_code == 2` |
| CM-T12 | module source | import audit | no non-stdlib imports |
