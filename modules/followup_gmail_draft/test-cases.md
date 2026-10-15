# followup_gmail_draft — Test Cases

Adapter tests use a fake MCP transport (no network).

| ID | Given | When | Then |
|---|---|---|---|
| GD-T1 | fake transport returns draft id `d1` | `McpGmailGateway.create_draft(draft)` | returns `DraftResult("d1", …)`; transport received exactly one call with `to`, `subject`, `body` |
| GD-T2 | `draft.to is None` | create | call made with empty recipient; no invented address |
| GD-T3 | server command missing / cannot start | create | `AppError` exit 1, message starts `Gmail connector unavailable` |
| GD-T4 | call exceeds timeout | create | `AppError` exit 1, "unavailable" (no hang) |
| GD-T5 | transport returns auth error | create | `AppError` exit 1, `not authenticated` message |
| GD-T6 | transport returns other error | create | `AppError` exit 1, `Gmail draft failed: <msg>` |
| GD-T7 | response with no draft id | create | `AppError` |
| GD-T8 | **AC-13** scan module source and the allow-list | static test | no send operation referenced; allow-list has exactly one non-`send` tool |
| GD-T9 | tool name configured as `send_email` / `gmail_send` | construct or create | refused with `AppError`; transport never called |
| GD-T10 | `DraftGateway` protocol | inspect | has only `create_draft` |
| GD-T11 | `DryRunGateway` with a `StringIO` | create | output contains subject, to (or `(none)`), body; returns `DraftResult("dry-run")`; no process/network call |
| GD-T12 | `FakeGateway` used twice | create ×2 | `drafts` contains both, in order |
| GD-T13 | other commands run without the MCP library installed | import module | import succeeds (lazy import) |
| GD-T14 | log output in normal mode | create | body not logged; only with `--verbose` |
| GD-T15 | **Manual smoke** real account | create | draft in Gmail Drafts folder; nothing in Sent |
