# ingest_note_parser — Test Cases

| ID | Given | When | Then |
|---|---|---|---|
| NP-T1 | valid note: date, 3 attendees, 3 item lines | `parse_note` | `Note` with date, 3 `Person`s, 3 `RawItemLine`s |
| NP-T2 | `- [ ] A` and `- [x] B` and `- [X] C` | parse | `checked` False, True, True |
| NP-T3 | attendee `Priya Sharma <priya@x.com>` | parse | `Person("Priya Sharma","priya@x.com")` |
| NP-T4 | attendee `Rahul Mehta` (no email) | parse | `Person("Rahul Mehta", None)` |
| NP-T5 | no `---` at top | parse | `MalformedNote` "missing front matter" |
| NP-T6 | opening `---` but no closing | parse | `MalformedNote` |
| NP-T7 | front matter `date: [unclosed` | parse | `MalformedNote` "invalid front matter" |
| NP-T8 | front matter is a YAML list, not a mapping | parse | `MalformedNote` |
| NP-T9 | `date` missing | parse | `MalformedNote` "missing or invalid date" |
| NP-T10 | `date: 2026-13-45` / `date: 12 Oct` | parse | `MalformedNote` for each |
| NP-T11 | quoted `date: "2026-10-12"` | parse | valid, same result as unquoted |
| NP-T12 | `attendees` missing / `[]` | parse | `MalformedNote` "missing or empty attendees" |
| NP-T13 | attendee entry is a number or blank | parse | `MalformedNote` |
| NP-T14 | empty string / whitespace only | parse | `MalformedNote` "empty file" |
| NP-T15 | valid front matter, body without items | parse | valid `Note`, `lines == ()` |
| NP-T16 | `- [ ]` with no text | parse | line ignored |
| NP-T17 | item lines at file lines 9, 11 | parse | `line_no` 9, 11 (original file numbering) |
| NP-T18 | plain bullets `- text` and prose | parse | ignored |
| NP-T19 | CRLF line endings and leading BOM | parse | parses identically to LF version |
| NP-T20 | same attendee listed twice | parse | one `Person` |
| NP-T21 | front matter with `!!python/object` tag | parse | `MalformedNote` (safe_load rejects) |
| NP-T22 | indented item `  - [ ] nested` | parse | recognised as an item |
