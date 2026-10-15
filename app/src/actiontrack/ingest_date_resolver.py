"""Find a due-date phrase in task text and resolve it against the meeting date (pure)."""
from __future__ import annotations

import calendar
import difflib
import re
from dataclasses import dataclass
from datetime import date, timedelta

_MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
           "september", "october", "november", "december"]
_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_MON = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_DAY = r"mon(?:day)?|tue(?:s(?:day)?)?|wed(?:nesday)?|thu(?:r(?:s(?:day)?)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?"
_DOW = rf"(?:(?:{_DAY})\.?,?\s+)?"  # optional leading weekday: "Wed 16 Sep", "Saturday 10 Oct"
_ORD = r"(?:st|nd|rd|th)?"
_KEYWORDS = set(_MONTHS + _DAYS + ["today", "tomorrow", "next", "end", "eow", "eom", "eod", "mid"])


@dataclass(frozen=True)
class DueResult:
    due: date | None
    task_text: str            # phrase removed if resolved; unchanged otherwise
    warning: str | None = None


def _month(s: str) -> int:
    return next(i for i, m in enumerate(_MONTHS, 1) if m.startswith(s[:3].lower()))


def _dow(s: str) -> int:
    return next(i for i, w in enumerate(_DAYS) if w.startswith(s[:3].lower()))


def _next_monday(d: date) -> date:
    return d + timedelta((-d.weekday()) % 7 or 7)  # strictly after d


def _eom(m: date) -> date:
    return m.replace(day=calendar.monthrange(m.year, m.month)[1])


# (regex, fn(match, meeting) -> date); fn may raise ValueError for impossible dates.
_EXPRS = [
    (r"(\d{4})-(\d{2})-(\d{2})", lambda m, d: date(int(m[1]), int(m[2]), int(m[3]))),
    (rf"{_DOW}(\d{{1,2}}){_ORD}\s+{_MON}\.?(?:,?\s+(\d{{4}}))?",
     lambda m, d: date(int(m[3] or d.year), _month(m[2]), int(m[1]))),
    (rf"{_DOW}{_MON}\.?\s+(\d{{1,2}}){_ORD}(?:,?\s+(\d{{4}}))?",
     lambda m, d: date(int(m[3] or d.year), _month(m[1]), int(m[2]))),
    (rf"mid[-\s]{_MON}", lambda m, d: date(d.year, _month(m[1]), 15)),
    (rf"next\s+({_DAY})", lambda m, d: _next_monday(d) + timedelta(_dow(m[1]))),  # that day, next week
    (rf"({_DAY})", lambda m, d: d + timedelta((_dow(m[1]) - d.weekday()) % 7 or 7)),
    (r"today", lambda m, d: d),
    (r"tomorrow", lambda m, d: d + timedelta(1)),
    (r"next\s+week", lambda m, d: _next_monday(d)),
    (r"end\s+of\s+next\s+week", lambda m, d: _next_monday(d) + timedelta(4)),
    (r"end\s+of\s+week|eow", lambda m, d: d + timedelta((4 - d.weekday()) % 7)),
    (r"end\s+of\s+month|eom", lambda m, d: _eom(d)),
    (r"(?:eod|end\s+of\s+day)\s+tomorrow", lambda m, d: d + timedelta(1)),
    (r"eod|end\s+of\s+day", lambda m, d: d),
]
_EXPRS = [(re.compile(p + r"\b", re.I), f) for p, f in _EXPRS]
_INTRO = re.compile(r"\b(?:by|before|on|due|until)\b:?\s+", re.I)
_TRAIL = re.compile(r"[\s.!?,;]*$")


def _expr_at(text: str, pos: int, meeting: date):
    """Return (end, date|None) for the first expression matching at pos, else None.
    date is None when the text matched a date shape but is impossible (31 Feb)."""
    for rx, fn in _EXPRS:
        m = rx.match(text, pos)
        if m:
            try:
                return m.end(), fn(m, meeting)
            except ValueError:
                return m.end(), None
    return None


def _date_like(word: str) -> bool:
    w = word.lower().strip(".,;:!?")
    return bool(re.search(r"\d", w)) or w in _KEYWORDS or bool(difflib.get_close_matches(w, _KEYWORDS, 1, 0.8))


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,;.])", r"\1", text)
    text = text.strip(" ,;:.-–—")
    return re.sub(r"\s+(?:for|from|on|at|to|in)$", "", text, flags=re.I)  # left dangling by a removed date


def resolve_due(text: str, meeting_date: date) -> DueResult:
    failure = None  # first date-looking introducer phrase that could not be resolved
    for intro in _INTRO.finditer(text):
        hit = _expr_at(text, intro.end(), meeting_date)
        if hit is None:
            word = re.match(r"\S+", text[intro.end():])
            if word and _date_like(word[0]) and failure is None:
                failure = text[intro.start():intro.end() + word.end()]
            continue
        end, due = hit
        if due is None:
            failure = failure or text[intro.start():end]
            continue
        return DueResult(due, _tidy(text[:intro.start()] + " " + text[end:]))
    # trailing expression with no introducer
    best = None
    for rx, fn in _EXPRS:
        for m in re.finditer(rx.pattern, text, re.I):
            if (m.start() == 0 or not text[m.start() - 1].isalnum()) and _TRAIL.fullmatch(text, m.end()):
                if best is None or m.start() < best[0].start():
                    best = (m, fn)
                break
    if best:
        m, fn = best
        try:
            return DueResult(fn(m, meeting_date), _tidy(text[:m.start()]))
        except ValueError:
            failure = failure or m[0]
    if failure:
        return DueResult(None, text, f"could not resolve due date: '{failure}'")
    return DueResult(None, text)
