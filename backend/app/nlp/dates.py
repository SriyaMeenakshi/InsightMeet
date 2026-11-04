"""Deadline / date expression detection and normalisation.

Relative expressions ("Friday", "next week") are only converted to calendar
dates when a meeting (reference) date is supplied.  Without it they stay
*unresolved* and keep their raw wording - we never guess a date.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

from .lexicon import MONTHS, WEEKDAYS

_MONTH_ALT = (
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
    r"sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
)
_WD_ALT = r"monday|tuesday|tues|tue|wednesday|wed|thursday|thurs|thur|thu|friday|fri|saturday|sunday"
_ANCHOR = r"(?:(?:by|before|until|till|on|due|for)\s+)?"
_EVENTS = (
    r"demo|review|presentation|submission|release|launch|sprint|deadline|standup|"
    r"stand-up|viva|client meeting|next meeting|exam|kickoff|kick-off|handover|go-live"
)

# Order matters: more specific first.  Each entry: (kind_tag, compiled regex)
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("iso", re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")),
    ("month_day", re.compile(
        rf"\b{_ANCHOR}(?:the\s+)?({_MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,?\s+(\d{{4}}))?\b", re.I)),
    ("day_month", re.compile(
        rf"\b{_ANCHOR}(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_ALT})\.?(?:,?\s+(\d{{4}}))?\b", re.I)),
    ("numeric", re.compile(rf"\b{_ANCHOR}(\d{{1,2}})/(\d{{1,2}})(?:/(\d{{2,4}}))?\b", re.I)),
    ("in_n", re.compile(r"\bin\s+(\d{1,2}|a|an|one|two|three|four|five|six|seven|ten)\s+(day|week|month|hour)s?\b", re.I)),
    ("end_of", re.compile(
        r"\b(?:by\s+|before\s+)?(?:the\s+)?(end of (?:the |this |next )?(?:day|week|month|sprint)|eod|eow|eom|close of business|cob)\b", re.I)),
    ("day_after_tomorrow", re.compile(r"\b(?:the\s+)?day after tomorrow\b", re.I)),
    ("weekday", re.compile(rf"\b{_ANCHOR}(?:(next|this|coming|upcoming)\s+)?({_WD_ALT})\b", re.I)),
    ("period", re.compile(r"\b(?:by\s+|before\s+|within\s+|in\s+)?(?:the\s+)?(next week|this week|next month|this month|next weekend|this weekend)\b", re.I)),
    ("simple", re.compile(r"\b(today|tonight|tomorrow|this evening|this afternoon|this morning)\b", re.I)),
    ("asap", re.compile(r"\b(asap|as soon as possible|immediately|right away|urgent(?:ly)?)\b", re.I)),
    ("event", re.compile(rf"\b(?:by|before|until|after|for)\s+(?:the\s+)?({_EVENTS})\b", re.I)),
]


@dataclass
class DateMatch:
    raw: str
    start: int
    end: int
    kind: str                # absolute | relative | event | unresolved
    resolved: bool
    date: date | None
    precision: str           # day | week | month | unknown
    normalized: str
    note: str | None = None


def _month_num(token: str) -> int:
    token = token.lower()[:3]
    return [m[:3] for m in MONTHS].index(token) + 1


def _wd_num(token: str) -> int:
    return [w[:3] for w in WEEKDAYS].index(token.lower()[:3])


def _next_weekday(ref: date, wd: int, strictly_after: bool = False) -> date:
    delta = (wd - ref.weekday()) % 7
    if delta == 0 and strictly_after:
        delta = 7
    return ref + timedelta(days=delta)


def _fmt(d: date) -> str:
    return d.strftime("%a %d %b %Y")


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


_NUMWORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
             "five": 5, "six": 6, "seven": 7, "ten": 10}


def _resolve(tag: str, m: re.Match, ref: date | None) -> DateMatch:
    raw = m.group(0).strip()
    start, end = m.start(), m.end()

    def mk(kind, resolved, d, precision, normalized, note=None):
        return DateMatch(raw, start, end, kind, resolved, d, precision, normalized, note)

    if tag == "iso":
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return mk("absolute", d is not None, d, "day", _fmt(d) if d else raw)

    if tag in ("month_day", "day_month"):
        if tag == "month_day":
            mon, day, year = _month_num(m.group(1)), int(m.group(2)), m.group(3)
        else:
            day, mon, year = int(m.group(1)), _month_num(m.group(2)), m.group(3)
        if year:
            d = _safe_date(int(year), mon, day)
            return mk("absolute", d is not None, d, "day", _fmt(d) if d else raw)
        label = f"{day} {calendar.month_abbr[mon]}"
        if ref is None:
            return mk("absolute", False, None, "unknown", f"{label} (year unknown)",
                      "No meeting date supplied, so the year is not assumed.")
        d = _safe_date(ref.year, mon, day)
        if d and d < ref - timedelta(days=30):
            d = _safe_date(ref.year + 1, mon, day)
        return mk("absolute", d is not None, d, "day", _fmt(d) if d else raw,
                  "Year taken from the meeting date.")

    if tag == "numeric":
        a, b = int(m.group(1)), int(m.group(2))
        year = m.group(3)
        if year and len(year) == 2:
            year = "20" + year
        if a > 12 and b <= 12:
            day, mon = a, b
        elif b > 12 and a <= 12:
            mon, day = a, b
        elif a == b:
            day, mon = a, b
        else:
            return mk("unresolved", False, None, "unknown", raw,
                      "Ambiguous numeric date (day/month or month/day).")
        y = int(year) if year else (ref.year if ref else None)
        if y is None:
            return mk("absolute", False, None, "unknown", raw, "Year unknown without a meeting date.")
        d = _safe_date(y, mon, day)
        return mk("absolute", d is not None, d, "day", _fmt(d) if d else raw)

    if tag == "day_after_tomorrow":
        if ref is None:
            return mk("relative", False, None, "unknown", raw, "Needs a meeting date.")
        d = ref + timedelta(days=2)
        return mk("relative", True, d, "day", _fmt(d))

    if tag == "simple":
        word = m.group(1).lower()
        if ref is None:
            return mk("relative", False, None, "unknown", word, "Needs a meeting date.")
        d = ref + timedelta(days=1) if word == "tomorrow" else ref
        return mk("relative", True, d, "day", _fmt(d))

    if tag == "weekday":
        qual = (m.group(1) or "").lower()
        wd = _wd_num(m.group(2))
        label = f"{qual + ' ' if qual else ''}{WEEKDAYS[wd].capitalize()}"
        if ref is None:
            return mk("relative", False, None, "unknown", label, "Needs a meeting date.")
        d = _next_weekday(ref, wd, strictly_after=True)
        if qual == "next" and d - ref < timedelta(days=(7 - ref.weekday())):
            d += timedelta(days=7)  # "next Friday" = the Friday of next week
        return mk("relative", True, d, "day", _fmt(d),
                  "Next occurrence of that weekday after the meeting date.")

    if tag == "in_n":
        n = m.group(1).lower()
        n = int(n) if n.isdigit() else _NUMWORDS.get(n, 1)
        unit = m.group(2).lower()
        if ref is None or unit == "hour":
            return mk("relative", False, None, "unknown", raw, "Needs a meeting date." if unit != "hour" else None)
        days = {"day": n, "week": 7 * n, "month": 30 * n}[unit]
        d = ref + timedelta(days=days)
        return mk("relative", True, d, "day" if unit == "day" else "week", _fmt(d),
                  "Approximate" if unit == "month" else None)

    if tag == "end_of":
        phrase = m.group(1).lower()
        if ref is None:
            return mk("relative", False, None, "unknown", phrase, "Needs a meeting date.")
        if phrase in ("eod", "close of business", "cob") or phrase.endswith("day"):
            return mk("relative", True, ref, "day", _fmt(ref))
        if phrase in ("eow",) or phrase.endswith("week"):
            base = ref + timedelta(days=7) if "next" in phrase else ref
            d = base + timedelta(days=4 - base.weekday()) if base.weekday() <= 4 else base + timedelta(days=(4 - base.weekday()) % 7)
            return mk("relative", True, d, "week", _fmt(d), "End of week taken as Friday.")
        if phrase in ("eom",) or phrase.endswith("month"):
            base = ref
            if "next" in phrase:
                base = (ref.replace(day=1) + timedelta(days=32)).replace(day=1)
            last = calendar.monthrange(base.year, base.month)[1]
            return mk("relative", True, base.replace(day=last), "month", _fmt(base.replace(day=last)))
        return mk("relative", False, None, "unknown", phrase, "Sprint length is not known.")

    if tag == "period":
        phrase = m.group(1).lower()
        if ref is None:
            return mk("relative", False, None, "unknown", phrase, "Needs a meeting date.")
        if "week" in phrase and "weekend" not in phrase:
            base = ref + timedelta(days=7) if "next" in phrase else ref
            d = base + timedelta(days=(4 - base.weekday()) % 7 if base.weekday() > 4 else 4 - base.weekday())
            return mk("relative", True, d, "week", _fmt(d), "Interpreted as the end (Friday) of that week.")
        if "weekend" in phrase:
            base = ref + timedelta(days=7) if "next" in phrase else ref
            d = base + timedelta(days=(5 - base.weekday()) % 7)
            return mk("relative", True, d, "week", _fmt(d), "Interpreted as the Saturday of that weekend.")
        base = ref
        if "next" in phrase:
            base = (ref.replace(day=1) + timedelta(days=32)).replace(day=1)
        last = calendar.monthrange(base.year, base.month)[1]
        d = base.replace(day=last)
        return mk("relative", True, d, "month", _fmt(d), "Interpreted as the end of that month.")

    if tag == "asap":
        return mk("unresolved", False, None, "unknown", m.group(1).lower(), "Urgency without a date.")

    if tag == "event":
        return mk("event", False, None, "unknown", f"before/at the {m.group(1).lower()}",
                  "Tied to an event; the event date is not stated.")

    return mk("unresolved", False, None, "unknown", raw)


def find_dates(text: str, ref: date | None = None) -> list[DateMatch]:
    """Find all date / deadline expressions in `text` (non-overlapping)."""
    found: list[DateMatch] = []
    taken: list[tuple[int, int]] = []
    for tag, rx in _PATTERNS:
        for m in rx.finditer(text):
            s, e = m.span()
            if any(not (e <= ts or s >= te) for ts, te in taken):
                continue
            taken.append((s, e))
            found.append(_resolve(tag, m, ref))
    found.sort(key=lambda d: d.start)
    return found


def parse_meeting_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        raise ValueError("meeting_date must be an ISO date such as 2025-03-14")
