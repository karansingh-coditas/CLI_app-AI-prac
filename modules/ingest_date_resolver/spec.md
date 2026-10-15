# ingest_date_resolver — Spec

**Family:** `ingest_` · **File:** `src/actiontrack/ingest_date_resolver.py` · **Depends on:** stdlib `datetime`, `re` only (no project modules)

## Purpose
Find a due-date phrase in a task text, resolve it to a real date relative to the **meeting date**, and return the text with that phrase removed. Pure function; never reads the clock.

## Requirements covered
FR-P2, FR-E18 (bad phrase → no date, text kept), AC-3.

## Public interface

```python
@dataclass(frozen=True)
class DueResult:
    due: date | None
    task_text: str            # phrase removed if resolved; unchanged otherwise
    warning: str | None = None

def resolve_due(text: str, meeting_date: date) -> DueResult
```

## Phrase location
A due phrase is `by|before|on|due|until` followed by a date expression, **or** a trailing date expression at the end of the text. The first introducer wins when several exist.

## Supported expressions (case-insensitive)

| Expression | Resolves to |
|---|---|
| `2026-10-30` | that date |
| `30 Oct`, `30 October`, `Oct 30`, `October 30` | that day, in the **meeting's year** |
| `30 Oct 2026`, `Oct 30, 2026` | that date |
| `Monday` … `Sunday` (also `Mon`, `Tue`…) | next occurrence **strictly after** the meeting date. If the meeting is on that weekday → +7 days |
| `today` | meeting date |
| `tomorrow` | meeting date + 1 |
| `next week` | the coming Monday (strictly after the meeting date) |
| `end of week`, `eow` | the Friday on or after the meeting date (Sat/Sun → following Friday) |
| `end of month`, `eom` | last day of the meeting's month |

## Rules
1. Resolved → `due=<date>`, the introducer + expression are removed from `task_text`, leftover whitespace/trailing punctuation tidied.
2. A phrase is found but is not valid (`by 31 Feb`, `by Fiday`, `by soon`) → `due=None`, `task_text` **unchanged**, `warning="could not resolve due date: '<phrase>'"`.
3. No introducer and no trailing date → `due=None`, no warning.
4. `before X` resolves to `X` itself (the stated date is stored, not the day before). `X` is the stated limit. This is a documented simplification.
5. The meeting date is the sole anchor; wall-clock "today" is never used (NFR-8).
6. Never raises.

## Known ceiling
Year-less dates always use the meeting's year, so `by 5 Jan` in a December meeting resolves to the same December's January (in the past). Needs a year-rollover rule if it proves common.

## Out of scope
Times of day, ranges (`Mon–Wed`), non-English phrases, ordinals (`30th`) — v1 treats them as unresolved (warning).

## Amendment — real sample notes (2026-10-15)
Added expressions: ordinals (`Oct 3rd`, `5th Oct`); leading weekday on a date (`Wed 16 Sep`, `Saturday 10 Oct`); `EOD`/`end of day` (= meeting date), `EOD tomorrow`; `end of next week` (Friday of the following week); `next <weekday>` (that weekday in the following Mon–Sun week); `mid-October` (the 15th, meeting year).
Phrase search: the first introducer that **resolves** wins (an earlier non-date such as `by 10%` is skipped). Cleanup also strips dangling `—`/`–` and a trailing `for|from|on|at|to|in` left by the removed date.
Ordinals are no longer "unresolved" (supersedes Out of scope).
