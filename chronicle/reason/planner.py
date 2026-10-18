"""Rule-based starter planner. Replace/augment with structured Nemotron planning."""
import re
from datetime import date
from .models import QueryPlan

ISO_DATE = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
MONTHS = "January February March April May June July August September October November December".split()
MONTH_PATTERN = "|".join(f"{month}|{month[:3]}" for month in MONTHS)
NAMED_DATE = re.compile(
    rf"\b(?:({MONTH_PATTERN})\s+(\d{{1,2}})(?:st|nd|rd|th)?|"
    rf"(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_PATTERN}))(?:,?\s+(\d{{4}}))?\b",
    re.IGNORECASE,
)


class InvalidQueryDate(ValueError):
    """An explicit date in the question is not a calendar date."""


def plan_query(question: str, as_of: date | None = None) -> QueryPlan:
    lower = question.lower()
    history = any(word in lower for word in ("before", "after", "earlier than", "later than", "history"))
    match = ISO_DATE.search(question)
    named = NAMED_DATE.search(question)
    ref = None
    try:
        if match:
            ref = date.fromisoformat(match.group(1))
        elif named:
            month = named.group(1) or named.group(4)
            month_number = next(i for i, name in enumerate(MONTHS, 1) if name.lower().startswith(month.lower()))
            ref = date(int(named.group(5) or (as_of or date.today()).year),
                       month_number, int(named.group(2) or named.group(3)))
    except ValueError as exc:
        raise InvalidQueryDate("The question contains an invalid calendar date") from exc
    if history:
        # Keep both sides of changes available for comparisons and ordering.
        kind = "ordering_or_history"
        ref = None
    elif ref or as_of:
        ref = ref or as_of
        kind = "as_of"
    elif any(word in lower for word in ("currently", "now", "latest", "current")):
        kind = "current"
    else:
        kind = "search"
    return QueryPlan(question=question, kind=kind, reference_date=ref)
