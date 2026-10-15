# ingest_owner_resolver — Test Cases

Attendees unless stated: Priya Sharma, Rahul Mehta (one Priya).

| ID | Text | Then |
|---|---|---|
| OR-T1 | `Priya to send the revised quote by Friday` | `resolved`, owner Priya Sharma, task_text `send the revised quote by Friday` |
| OR-T2 | `Rahul will share the deck` | `resolved`, owner Rahul Mehta, task_text `share the deck` |
| OR-T3 | `priya TO send quote` (case) | `resolved` |
| OR-T4 | `Priya Sharma to send quote` | `resolved` (full name) |
| OR-T5 | `Update the onboarding doc` | `none`, text unchanged |
| OR-T6 | `Ask Priya to review the draft` | `none` (name not at start) |
| OR-T7 | `Anita to book the room` (not an attendee) | `unknown`, owner None, text unchanged, note mentions Anita |
| OR-T8 | `Priya to send` and `Priya` has no `to` rest e.g. `Priya to` | `none` (empty rest) |

Attendees for T9–T13: Priya Sharma, Priya Nair, Rahul Mehta.

| ID | Text | Then |
|---|---|---|
| OR-T9 | `Priya to send quote` | `ambiguous`, owner None, candidates both Priyas, note `ambiguous owner: Priya (Priya Sharma \| Priya Nair)`, text unchanged |
| OR-T10 | `Priya S. to send quote` | `resolved`, Priya Sharma |
| OR-T11 | `Priya Nair to send quote` | `resolved`, Priya Nair |
| OR-T12 | `Priya N to send quote` (no dot) | `resolved`, Priya Nair |
| OR-T13 | `Rahul to send quote` | `resolved` despite other Priyas present |
| OR-T14 | attendees: two `Sam Lee` with different emails; text `Sam Lee to fix` | `ambiguous` |
| OR-T15 | attendee `Mary-Jane O'Neil`; text `Mary-Jane to call` | `resolved` |
| OR-T16 | attendee `Zoë Ünal`; text `Zoë to call` | `resolved` |
| OR-T17 | `Priya will send quote` | `resolved` (`will` form) |
| OR-T18 | `Update to docs` | `unknown` (documented false-positive), never raises |
| OR-T19 | attendee list empty | `unknown` or `none`, never raises |
| OR-T20 | module purity | no I/O or non-stdlib imports |
