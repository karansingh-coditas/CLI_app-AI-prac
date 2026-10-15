# track_owner_lookup — Test Cases

Owners: Priya Sharma `ps@x.com`, Priya Nair `pn@x.com`, Rahul Mehta `rahul@x.com`.

| ID | Query | Then |
|---|---|---|
| OL-T1 | `Rahul` | `found` Rahul Mehta |
| OL-T2 | `rahul` / `  RAHUL  ` | `found` (case and whitespace insensitive) |
| OL-T3 | `Rahul Mehta` | `found` |
| OL-T4 | `rahul@x.com` / `RAHUL@X.COM` | `found` |
| OL-T5 | `Priya` | `ambiguous`, candidates Priya Nair, Priya Sharma (sorted) (**AC-11**) |
| OL-T6 | `Priya Sharma` | `found` Priya Sharma |
| OL-T7 | `pn@x.com` | `found` Priya Nair |
| OL-T8 | `Anita` | `not_found` |
| OL-T9 | `Pri` (prefix) | `not_found` (no partial matching) |
| OL-T10 | `` / `   ` | `not_found` |
| OL-T11 | `unassigned` / `(unassigned)` / `UNASSIGNED` | `unassigned` |
| OL-T12 | owners include two `Sam Lee` with different emails; query `Sam Lee` | `ambiguous` |
| OL-T13 | same, query by one email | `found` |
| OL-T14 | owners list empty | any name → `not_found` |
| OL-T15 | owner without email (`Dev Patel`), query `Dev` | `found` |
| OL-T16 | module purity | imports only `core_models`; never raises |
