# followup_gmail_draft — Plan

## Approach
Define the tiny `DraftGateway` protocol first, ship `FakeGateway` and `DryRunGateway` immediately (they unblock `followup_runner`), then build the real MCP adapter after a short spike.

## Design decisions
- **Protocol with one method** is the entire contract to the rest of the app. This is what keeps Gmail loosely coupled: swapping the transport touches only this file.
- **"Never send" enforced three ways:** (1) no send method exists, (2) allow-list of exactly one connector tool, (3) a test that scans the source and the tool allow-list for `send` (AC-13).
- **Errors as `AppError(exit_code=1)`** (defined in `core_models`), so `followup_runner` needs no gateway-specific exception types.
- **Lazy MCP import and lazy construction** (done in `cli_app` only for non-dry-run), so `ingest`/`list`/`done` never need Gmail.
- **Timeout** on the connector call to avoid hanging the CLI.

## Steps
1. **Spike (GD-1):** discover the Gmail connector's create-draft tool name and schema, and decide the transport for a Python process (e.g. MCP Python SDK stdio client against a configured server command). Record the answer here and close Q-8.
2. `DraftGateway`, `FakeGateway`, `DryRunGateway`.
3. `McpGmailGateway`: start/connect, call create-draft tool with `to/subject/body`, map responses and errors.
4. Allow-list + `send` refusal.
5. Tests (fake transport for adapter logic; one optional manual smoke test against a real account, not in CI).

## Risks
- **Q-8 unresolved** → adapter may need a different transport than assumed. Mitigation: spike first; nothing else depends on it.
- Authentication flow may be interactive and outside the CLI. Mitigation: fail with a clear message (FR-F8); do not try to authenticate silently.
- A draft with empty `to` may be rejected by the connector: surface the connector's message.

## Definition of done
All `test-cases.md` pass (the manual smoke test recorded once), AC-13 test green.
