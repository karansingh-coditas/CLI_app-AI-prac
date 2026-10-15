# ingest_note_parser — Spec

**Family:** `ingest_` · **File:** `src/actiontrack/ingest_note_parser.py` · **Depends on:** `core_models`, PyYAML (`safe_load`)

## Purpose
Turn the raw text of one `.md` file into a `Note`, or reject it as malformed. Pure: takes text, does no file I/O.

## Requirements covered
FR-N1, FR-N2, FR-N3, FR-P3 (checked flag), FR-E16 (reject whole note), §7.4 malformed definition.

## Public interface

```python
def parse_note(path: str, text: str) -> Note      # raises MalformedNote(reason)
```

## Rules
1. Text must start with `---` on the first line, and have a closing `---` line. Otherwise `MalformedNote("missing front matter")`.
2. Front matter is parsed with `yaml.safe_load`. Invalid YAML, or a non-mapping result → `MalformedNote("invalid front matter")`.
3. `date`: required. Accept a YAML date or an ISO `YYYY-MM-DD` string. Missing / other format / impossible date → `MalformedNote("missing or invalid date")`.
4. `attendees`: required, non-empty list of strings. Each entry is `Full Name` or `Full Name <email>`. Whitespace is trimmed. An entry with no name part is malformed. Empty or missing → `MalformedNote("missing or empty attendees")`.
5. Body = everything after the closing `---`. An action item line matches `^\s*[-*]\s+\[( |x|X)\]\s+(.+?)\s*$`. `x`/`X` → `checked=True`. Line numbers are 1-based in the **original file**. Non-matching lines are ignored. Empty item text (`- [ ]` alone) is ignored.
6. Empty file / whitespace-only text → `MalformedNote("empty file")`.
7. A note with valid front matter and **zero** items is valid (returns `lines=()`).
8. Duplicate attendee entries (same `Person.key`) are collapsed to one.
9. Never raises anything but `MalformedNote`. Unexpected YAML objects are treated as invalid front matter.
10. Does not interpret owner or due-date text. That is the job of the sibling resolvers.

## Not handled here
Decoding bytes (the `ingest_runner` reads files as UTF-8 and reports decode failures as malformed), recursion, owner/date resolution.

## Amendment — real sample notes (2026-10-15)
Driven by `tests/fixtures/notes/` (36 real notes):
- **Two header styles.** YAML front matter, or plain header lines `Date: …` / `Attendees: A, B <e@x>` before the first blank line. Neither present → `missing front matter`.
- **Date forms:** ISO, `9 September 2026`, `Sep 9, 2026`, optional leading weekday (`Monday, 14 September 2026`). Anything else (`sometime last week`) → malformed.
- **Bullets:** `-`, `*`, `+`; nested (indented) items count.
- **Not items:** fenced code blocks, HTML comments (single or multi-line), `>` quotes, tables.
- **`Note.unrecognised`:** `ACTION:`/`TODO:` lines and rows of a table whose header contains "action" are returned here. They are **not stored**; `ingest_runner` reports each as `UNPARSEABLE_ITEM` so nothing is dropped silently.
