# ingest_dedup — Test Cases

| ID | Given | When | Then |
|---|---|---|---|
| DD-T1 | `"Send the Revised Quote!"` vs `"send the revised quote"` | `normalise_task` | equal |
| DD-T2 | `"fix   bug — now"` and `"fix bug now"` (en dash, extra spaces) | normalise | equal |
| DD-T3 | `"“Quote” review"` (curly quotes) | normalise | `"quote review"` |
| DD-T4 | same owner Priya Sharma, same task text | `dedup_key` | equal keys |
| DD-T5 | same task, owners Priya Sharma vs Priya Nair | `dedup_key` | different keys (FR-E13) |
| DD-T6 | same task, one owner None | `dedup_key` | different keys |
| DD-T7 | both owners None, same task | `dedup_key` | equal keys |
| DD-T8 | reworded tasks (`send quote` vs `email quote`) | `dedup_key` | different keys (no fuzzy) |
| DD-T9 | existing open (note A, 10-05) + incoming open (note B, 10-12) | `merge` | primary A; `also_seen_in == [B]`; `changed=True` |
| DD-T10 | existing from note B (10-12), incoming from note A (10-05) | `merge` | primary becomes A; B moves to `also_seen_in` |
| DD-T11 | existing open, incoming done | `merge` | status done |
| DD-T12 | existing done, incoming open | `merge` | stays done (never reopen) |
| DD-T13 | existing due 10-16, incoming due 10-23 | `merge` | due 10-23; one `DUE_CHANGED` issue |
| DD-T14 | existing due 10-23, incoming due 10-16 | `merge` | keeps 10-23; no issue |
| DD-T15 | existing due None, incoming due 10-16 | `merge` | due 10-16; no `DUE_CHANGED` |
| DD-T16 | existing due 10-16, incoming None | `merge` | keeps 10-16 |
| DD-T17 | incoming identical, same source file | `merge` | `changed=False`, nothing added to `also_seen_in` |
| DD-T18 | merge A+B then merge B again | repeat | `also_seen_in` has B once |
| DD-T19 | `notes` differ on both items | `merge` | union, no repeats |
| DD-T20 | any merge | inspect inputs | neither argument mutated |
| DD-T21 | same date tie, different files | `merge` | existing stays primary |
