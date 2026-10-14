from dataclasses import dataclass
from datetime import date
from typing import Literal

QueryType = Literal["as_of", "current", "unsupported"]

@dataclass(frozen=True)
class QueryPlan:
    question_type: QueryType
    entity: str | None
    predicate: str | None
    reference_date: date | None

@dataclass(frozen=True)
class Evidence:
    subject: str
    predicate: str
    object: str
    valid_from: date
    valid_to: date | None  # exclusive
    doc_id: str
    quote: str
