# ingest_date_resolver — Plan

## Approach
Two-stage: (1) locate the phrase with a regex (introducer + candidate expression, or trailing expression), (2) evaluate the expression with a small ordered list of matchers. Stdlib only.

## Design decisions
- **No `dateutil` / `dateparser`:** they guess wildly (`"Friday"` relative to *today*, not the meeting date) and add a dependency. The supported grammar is tiny and fully specified.
- **Matchers as a list of `(regex, fn(match, meeting_date) -> date)`** tried in order; first success wins. Easy to extend.
- **Return the cleaned text** from here so `ingest_runner` stays dumb.
- Month names via a dict (`jan`..`dec`, full names) to avoid locale dependence.
- Weekday math: `delta = (target - meeting.weekday()) % 7 or 7`.

## Steps
1. Introducer detection and phrase extraction.
2. Matchers: ISO, written forms, weekday, relative words, end-of-week/month.
3. Text cleaning (remove phrase, collapse spaces, trim trailing punctuation).
4. Invalid-phrase path with warning.
5. Table-driven tests anchored to fixed meeting dates (Mon 2026-10-12, Fri 2026-10-16, Sat 2026-10-17).

## Risks
- Ambiguous words: "on call", "by hand", "due diligence" would be seen as introducers. They fall in the "unresolved" path with a warning and keep the text, so nothing is lost. Reduce noise by only warning when the phrase *looks* date-like (contains a digit, month, weekday or relative keyword).
- Leap-year and month-length edge cases: rely on `datetime`, catch `ValueError`.

## Definition of done
All `test-cases.md` pass with no clock access (verified by freezing/never importing `date.today`).
