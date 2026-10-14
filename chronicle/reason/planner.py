import re
from datetime import date
from .models import QueryPlan

DATE_PATTERN = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

def plan_query(question: str) -> QueryPlan:
    """Minimal rule-based planner; expand using Nemotron later."""
    q = question.lower()
    date_match = DATE_PATTERN.search(q)
    reference_date = date.fromisoformat(date_match.group(1)) if date_match else None
    if "payment" not in q or not any(word in q for word in ("manager", "manage", "owner", "own")):
        return QueryPlan("unsupported", None, None, reference_date)
    return QueryPlan("as_of" if reference_date else "current", "payments", "manager", reference_date)
