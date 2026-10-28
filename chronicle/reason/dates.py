"""Write the calendar date next to relative days in document text, so the model does not have to.

"What I need by Mon EOD", written on Wednesday 2026-05-20, becomes "by Mon [2026-05-25] EOD".
Models get this arithmetic wrong (the same question was answered 23, 24 and 25 May in three runs).
Only the text shown to the model is annotated; stored memory is unchanged.

* "next Wed" is the Wednesday of the following Monday-to-Sunday week (the common work usage);
* "this/coming Wed" and "by/until/before Wed" are the next Wednesday on or after the written date;
* "last Wed" is the one before it;
* a bare weekday could be either, depending on tense, so it gets both dates.
"""
import re
from datetime import date, timedelta

_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"
# "Sat"/"Sun" only capitalised: lowercase "sat" and "sun" are ordinary words.
_WEEKDAY = (r"(?:[Mm]on(?:day)?|[Tt]ue(?:s(?:day)?)?|[Ww]ed(?:s|nesday)?|[Tt]hu(?:r(?:s(?:day)?)?)?"
            r"|[Ff]ri(?:day)?|Sat(?:urday)?|Sun(?:day)?)")
# Not when a date already follows ("Wed 5/27", "Thursday, May 28", "Wed, 20 May"); a time
# ("Thursday 14:00") is not a date.
_NO_DATE_AFTER = rf"(?![,\s]*(?:\d{{1,2}}/\d|\d{{4}}-|\d{{1,2}}(?:st|nd|rd|th)?\b(?!:)|the\s+\d|{_MONTH}))"
_RELATIVE = re.compile(
    rf"\b(?:(?P<mod>next|this|coming|last|by|until|before)\s+)?(?P<day>{_WEEKDAY})\b{_NO_DATE_AFTER}",
    re.IGNORECASE)
_RELATIVE_CASE = re.compile(rf"(?:(?i:next|this|coming|last|by|until|before)\s+)?{_WEEKDAY}")
_DEICTIC = re.compile(r"\b(today|tonight|tomorrow|yesterday)\b(?!\s*\[)", re.IGNORECASE)
_DEICTIC_OFFSET = {"today": 0, "tonight": 0, "tomorrow": 1, "yesterday": -1}


def _weekday_date(written: date, mod: str, target: int) -> str:
    w = written.weekday()
    coming = written + timedelta(days=(target - w) % 7)
    past = written - timedelta(days=(w - target) % 7 or 7)
    if mod == "next":
        return (written + timedelta(days=7 - w + target)).isoformat()
    if mod in ("this", "coming", "by", "until", "before"):
        return coming.isoformat()
    if mod == "last":
        return past.isoformat()
    return f"{past.isoformat()} or {coming.isoformat()}"


def annotate_dates(text: str, written: str) -> str:
    """``text`` with ISO dates after relative days, resolved against the ``written`` date."""
    try:
        day = date.fromisoformat((written or "")[:10])
    except ValueError:
        return text

    def weekday(m: re.Match) -> str:
        # The case-sensitive pattern keeps lowercase "sat"/"sun" out; IGNORECASE is only for "Next".
        if not _RELATIVE_CASE.fullmatch(m.group(0)):
            return m.group(0)
        mod = (m.group("mod") or "").lower()
        return f"{m.group(0)} [{_weekday_date(day, mod, _DAYS[m.group('day')[:3].lower()])}]"

    text = _RELATIVE.sub(weekday, text)
    return _DEICTIC.sub(
        lambda m: f"{m.group(0)} [{(day + timedelta(days=_DEICTIC_OFFSET[m.group(1).lower()])).isoformat()}]",
        text)
