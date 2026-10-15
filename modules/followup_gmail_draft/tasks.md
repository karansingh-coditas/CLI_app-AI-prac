# followup_gmail_draft — Tasks

- [ ] GD-1 **Spike:** identify the Gmail MCP connector's create-draft tool name/arguments and the transport the Python CLI will use; write findings into `plan.md` (closes Q-8)
- [ ] GD-2 Define `DraftGateway` protocol
- [ ] GD-3 Implement `FakeGateway` (records drafts) — unblocks `followup_runner`
- [ ] GD-4 Implement `DryRunGateway` (prints subject/to/body to a stream)
- [ ] GD-5 Implement `McpGmailGateway.create_draft` (lazy MCP import, timeout, response parsing)
- [ ] GD-6 Map failures: unavailable / not authenticated / other → `AppError(exit_code=1)` with specified messages
- [ ] GD-7 Enforce single-tool allow-list; refuse any tool name containing `send`
- [ ] GD-8 Add source-scan test asserting no send path (AC-13)
- [ ] GD-9 Write `tests/test_followup_gmail_draft.py` for all cases in `test-cases.md`
- [ ] GD-10 Manual smoke test against a real Gmail account; confirm draft appears in Drafts and nothing in Sent
