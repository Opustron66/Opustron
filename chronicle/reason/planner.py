"""Query planning: regex dates and keywords first, then an optional cheap LLM pass that names
the entities, their aliases and the question type (``understand``)."""
import os
import re
import sys
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


def lexical_query(question: str) -> str:
    """Keep parsed calendar dates out of lexical ranking, not out of the question."""
    return " ".join(NAMED_DATE.sub(" ", ISO_DATE.sub(" ", question)).split())


def plan_query(question: str, as_of: date | None = None) -> QueryPlan:
    lower = question.lower()
    history = any(word in lower for word in ("before", "after", "earlier than", "later than", "history",
                                              "in between", "more than once", "in the order", "earliest first"))
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


UNDERSTAND_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {"type": "array", "items": {"type": "string"}},
        "aliases": {"type": "array", "items": {"type": "string"}},
        "search_terms": {"type": "array", "items": {"type": "string"}},
        "question_type": {"type": "string"},
    },
    "required": ["entities", "aliases", "search_terms", "question_type"],
}

UNDERSTAND_PROMPT = """You prepare a keyword search over a project corpus (emails and chat).
For the question, return JSON:
{"entities": [people, projects, sites, items, documents it names],
 "aliases": [other ways the corpus may write those names: short forms, first names, ids],
 "search_terms": [up to 8 words or short phrases likely to appear in the documents that answer it,
                  including synonyms of the key nouns and verbs],
 "question_type": one of "current", "as_of", "history", "ordering", "single_hop", "abstention_risk"}
"history" = how a value changed over time; "abstention_risk" = asks about an outcome or fact that
may never have happened or been recorded. Do not answer the question."""

QUESTION_TYPES = frozenset({"current", "as_of", "history", "ordering", "single_hop", "abstention_risk"})


def understanding_enabled() -> bool:
    return os.environ.get("CHRONICLE_QUERY_LLM", "1").lower() not in ("0", "false", "no", "off")


def understand(plan: QueryPlan, llm=None) -> QueryPlan:
    """Add LLM-suggested search terms and a question type to ``plan``. Never raises: on any
    failure the regex plan is used as it is. Regex dates stay the source of ``reference_date``."""
    if not understanding_enabled():
        return plan
    if llm is None:
        from chronicle.guard import llm
    try:
        data = llm.complete([{"role": "system", "content": UNDERSTAND_PROMPT},
                             {"role": "user", "content": plan.question}], schema=UNDERSTAND_SCHEMA)
    except Exception as exc:  # noqa: BLE001
        print(f"[chronicle] query understanding failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return plan
    if not isinstance(data, dict):
        return plan
    terms = []
    for key in ("entities", "aliases", "search_terms"):
        values = data.get(key)
        if isinstance(values, list):
            terms += [v.strip() for v in values if isinstance(v, str) and v.strip()]
    plan.terms = list(dict.fromkeys(terms))[:24]
    qtype = data.get("question_type")
    plan.question_type = qtype if qtype in QUESTION_TYPES else ""
    if plan.question_type in ("history", "ordering") and plan.kind != "as_of":
        plan.kind = "ordering_or_history"
    return plan
