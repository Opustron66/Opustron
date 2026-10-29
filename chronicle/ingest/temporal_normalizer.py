"""Temporal normalisation: resolve date expressions against the *document* date.

Never uses the wall clock: ``reference`` is always the source document's date.
Conventions (documented because they are ambiguous in English):
  * ``next <weekday>``  -> that weekday in the NEXT calendar week (Mon-Sun week after the reference's)
  * ``last <weekday>``  -> most recent such weekday strictly before it
  * ``this <weekday>`` / bare ``<weekday>`` -> first such weekday on/after it (bare = lower confidence)
Order of resolution: exact ISO -> rules -> dateparser (RELATIVE_BASE=reference) -> optional LLM fallback.
"""

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import dateparser
from dateutil.relativedelta import relativedelta

WEEKDAYS = {n.lower(): i for i, n in enumerate(calendar.day_name)}
WEEKDAYS.update({n.lower(): i for i, n in enumerate(calendar.day_abbr)})
MONTHS = {n.lower(): i for i, n in enumerate(calendar.month_name) if n}
MONTHS.update({n.lower(): i for i, n in enumerate(calendar.month_abbr) if n})
NUMBERS = {w: i for i, w in enumerate(
    ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"])}
NUMBERS.update({"a": 1, "an": 1, "couple": 2, "few": 3})
UNITS = r"(day|week|month|year)s?"
MAX_YEAR_DRIFT = 10  # dateparser results further than this from the document's year are rejected


@dataclass(frozen=True)
class Resolved:
    start: date | None
    end: date | None = None  # inclusive; None for a single day
    precision: str = "day"  # day | week | month | quarter | year
    confidence: float = 1.0
    method: str = "rule"


@dataclass
class NormalizerConfig:
    sprint_days: int = 14
    sprint_anchor: date | None = None  # a known sprint start; "end of sprint" is unresolved without it


def _num(tok: str) -> int | None:
    return int(tok) if tok.isdigit() else NUMBERS.get(tok)


def _shift(ref: date, n: int, unit: str) -> date:
    return ref + relativedelta(**{unit + "s": n})


def _month_range(y: int, m: int) -> Resolved:
    return Resolved(date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1]), "month")


def _week_range(d: date) -> Resolved:
    start = d - timedelta(days=d.weekday())
    return Resolved(start, start + timedelta(days=6), "week")


def _quarter_range(y: int, q: int) -> Resolved:
    m = 3 * (q - 1) + 1
    return Resolved(date(y, m, 1), date(y, m + 2, calendar.monthrange(y, m + 2)[1]), "quarter")


def _weekday_after(ref: date, wd: int, *, strict: bool) -> date:
    delta = (wd - ref.weekday()) % 7
    if delta == 0 and strict:
        delta = 7
    return ref + timedelta(days=delta)


def _weekday_before(ref: date, wd: int) -> date:
    return ref - timedelta(days=(ref.weekday() - wd) % 7 or 7)


def _period(kind: str, offset: int, ref: date) -> Resolved | None:
    if kind == "week":
        return _week_range(ref + timedelta(weeks=offset))
    if kind == "month":
        d = ref + relativedelta(months=offset)
        return _month_range(d.year, d.month)
    if kind == "quarter":
        idx = (ref.year * 4 + (ref.month - 1) // 3) + offset
        return _quarter_range(idx // 4, idx % 4 + 1)
    if kind == "year":
        y = ref.year + offset
        return Resolved(date(y, 1, 1), date(y, 12, 31), "year")
    return None


_ORD = r"(?:st|nd|rd|th)?"
_TO = r" ?(?:-|–|—|to|through|thru|until) ?"
# "may 5–18", "may 5 - june 2", "5–18 may", "5 may - 2 june", each with an optional ", 2026".
# dateparser reads the trailing day of "may 5–18" as a two-digit year (2118).
_MONTH_FIRST = re.compile(rf"([a-z]+) (\d{{1,2}}){_ORD}{_TO}(?:([a-z]+) )?(\d{{1,2}}){_ORD}(?:,? (\d{{4}}))?")
_DAY_FIRST = re.compile(rf"(\d{{1,2}}){_ORD}(?: ([a-z]+))?{_TO}(\d{{1,2}}){_ORD} ([a-z]+)(?:,? (\d{{4}}))?")


def _day_range(t: str, ref: date) -> Resolved | None:
    if m := _MONTH_FIRST.fullmatch(t):
        m1, d1, m2, d2, y = m[1], m[2], m[3] or m[1], m[4], m[5]
    elif m := _DAY_FIRST.fullmatch(t):
        d1, m1, d2, m2, y = m[1], m[2] or m[4], m[3], m[4], m[5]
    else:
        return None
    if m1 not in MONTHS or m2 not in MONTHS:
        return None
    year = int(y) if y else ref.year
    try:
        start, end = date(year, MONTHS[m1], int(d1)), date(year, MONTHS[m2], int(d2))
    except ValueError:
        return None
    if end < start:  # "dec 28 - jan 3"
        end = end.replace(year=year + 1)
    return Resolved(start, end, confidence=1.0 if y else 0.9)


def _rules(text: str, ref: date, cfg: NormalizerConfig) -> Resolved | None:
    t = re.sub(r"\s+", " ", text.lower().strip().rstrip(".,")).replace("the day after tomorrow", "in 2 days")
    t = re.sub(r"^(on|by|until|since|from|at) ", "", t)
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:[t ].*)?", t):
        return Resolved(date(*map(int, m.groups())), method="iso")
    simple = {"today": 0, "now": 0, "tomorrow": 1, "yesterday": -1, "day before yesterday": -2}
    if t in simple:
        return Resolved(ref + timedelta(days=simple[t]))
    if t in ("tonight", "this morning", "this afternoon", "this evening"):
        return Resolved(ref)
    if m := re.fullmatch(rf"in (\w+) {UNITS}", t):
        n = _num(m[1])
        return Resolved(_shift(ref, n, m[2])) if n is not None else None
    if m := re.fullmatch(rf"(\w+) {UNITS} (ago|from now|later)", t):
        n = _num(m[1])
        if n is None:
            return None
        return Resolved(_shift(ref, -n if m[3] == "ago" else n, m[2]), confidence=0.9 if m[2] in ("month", "year") else 1.0)
    if m := re.fullmatch(r"(next|last|this|previous) (week|month|quarter|year)", t):
        return _period(m[2], {"next": 1, "last": -1, "previous": -1, "this": 0}[m[1]], ref)
    if m := re.fullmatch(r"(next|last|this|previous) (\w+)", t) and t.split()[1] in WEEKDAYS:
        mod, wd = t.split()[0], WEEKDAYS[t.split()[1]]
        if mod == "next":
            return Resolved(ref - timedelta(days=ref.weekday()) + timedelta(weeks=1, days=wd))
        if mod in ("last", "previous"):
            return Resolved(_weekday_before(ref, wd))
        return Resolved(_weekday_after(ref, wd, strict=False), confidence=0.9)
    if t in WEEKDAYS:
        return Resolved(_weekday_after(ref, WEEKDAYS[t], strict=False), confidence=0.7)
    if m := re.fullmatch(r"(end|start|beginning) of (?:the |this |next |last )?(week|month|quarter|year)", t):
        offset = 1 if " next " in f" {t} " else -1 if " last " in f" {t} " else 0
        period = _period(m[2], offset, ref)
        return Resolved(period.end if m[1] == "end" else period.start, precision="day", confidence=0.9)
    if m := re.fullmatch(r"(end|start|beginning) of (?:the )?sprint", t):
        if cfg.sprint_anchor is None:
            return None
        n = (ref - cfg.sprint_anchor).days // cfg.sprint_days
        s = cfg.sprint_anchor + timedelta(days=n * cfg.sprint_days)
        return Resolved(s + timedelta(days=cfg.sprint_days - 1) if m[1] == "end" else s, confidence=0.8)
    if m := re.fullmatch(r"(?:q([1-4])|([1-4])q)(?: (\d{4}))?", t):
        return _quarter_range(int(m[3] or ref.year), int(m[1] or m[2]))
    if m := re.fullmatch(r"(\d{4})", t):
        return Resolved(date(int(m[1]), 1, 1), date(int(m[1]), 12, 31), "year")
    if m := re.fullmatch(r"([a-z]+)(?: (\d{4}))?", t) and t.split()[0] in MONTHS:
        parts = t.split()
        return _month_range(int(parts[1]) if len(parts) > 1 else ref.year, MONTHS[parts[0]])
    if (r := _day_range(t, ref)) is not None:
        return r
    if m := re.fullmatch(r"(?:(\d{1,2})(?:st|nd|rd|th)? ([a-z]+)|([a-z]+) (\d{1,2})(?:st|nd|rd|th)?)(?:,? (\d{4}))?", t):
        day = int(m[1] or m[4])
        mon = MONTHS.get(m[2] or m[3])
        if mon:
            y = int(m[5]) if m[5] else ref.year
            try:
                return Resolved(date(y, mon, day), confidence=1.0 if m[5] else 0.9)
            except ValueError:
                return None
    return None


def resolve(
    expr: str | date | datetime | None,
    reference: date,
    *,
    config: NormalizerConfig | None = None,
    llm_fallback: Callable[[str, date], Resolved | None] | None = None,
) -> Resolved:
    """Resolve ``expr`` relative to the source document's date ``reference``."""
    if expr is None or (isinstance(expr, str) and not expr.strip()):
        return Resolved(None, confidence=0.0, method="none")
    if isinstance(expr, datetime):
        return Resolved(expr.date(), method="iso")
    if isinstance(expr, date):
        return Resolved(expr, method="iso")
    if (r := _rules(expr, reference, config or NormalizerConfig())) is not None:
        return r
    parsed = dateparser.parse(
        expr,
        settings={"RELATIVE_BASE": datetime.combine(reference, datetime.min.time()),
                  "PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    # A year far from the document's is a misparse (e.g. a day read as a two-digit year).
    if parsed is not None and abs(parsed.year - reference.year) <= MAX_YEAR_DRIFT:
        return Resolved(parsed.date(), confidence=0.6, method="dateparser")
    if llm_fallback and (r := llm_fallback(expr, reference)) is not None:
        return r
    return Resolved(None, confidence=0.0, method="unresolved")


def normalize(value: str | datetime | None) -> datetime | None:
    """Normalize an ISO-8601 value, leaving missing values as ``None`` (legacy helper)."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
