# followup_compose — Test Cases

Today = 2026-10-15. Owner: Rahul Mehta `rahul@x.com`.

| ID | Given | When | Then |
|---|---|---|---|
| FC-T1 | 1 overdue (due 10-10) + 2 open (10-20, none) | `compose` | body has `Overdue` section first, then `Open`; `included_ids` in body order |
| FC-T2 | only open items | compose | no `Overdue` heading |
| FC-T3 | only overdue items | compose | no `Open` heading |
| FC-T4 | no items | compose | returns `None` |
| FC-T5 | only done items | compose | returns `None` |
| FC-T6 | items include another owner's open item | compose | other owner's item excluded |
| FC-T7 | duplicate item (same id) passed twice | compose | appears once (FR-E4) |
| FC-T8 | item due 10-10 | render | line shows due date and `5 days overdue` |
| FC-T9 | item due today (10-15) | compose | in `Open`, not `Overdue` |
| FC-T10 | undated item | render | line says `no due date`; not in `Overdue` |
| FC-T11 | owner with email | compose | `draft.to == "rahul@x.com"` |
| FC-T12 | owner without email | compose | `draft.to is None`; draft otherwise complete |
| FC-T13 | any | subject | `Action items follow-up — Rahul — 2026-10-15` |
| FC-T14 | any | body | starts `Hi Rahul,`; ends with closing; no sender name invented |
| FC-T15 | ordering in a section | compose | due ascending, undated last, ties by id |
| FC-T16 | task text with newline / double spaces | render | single clean line |
| FC-T17 | line content | render | includes source file stem and meeting date |
| FC-T18 | module purity | inspect | imports only `core_models`; no clock/I/O |
