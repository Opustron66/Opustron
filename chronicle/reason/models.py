from dataclasses import dataclass, field
from datetime import date

@dataclass
class QueryPlan:
    question: str
    kind: str = "search"
    reference_date: date | None = None

@dataclass
class Evidence:
    doc_id: str
    text: str
    date: str = ""
    score: float = 0.0
    kind: str = "claim"  # claim | topic | entity | chunk
    # Further documents this evidence quotes (a topic timeline cites one per entry).
    cites: list[str] = field(default_factory=list)

@dataclass
class AnswerResult:
    answer: str
    source_ids: list[str] = field(default_factory=list)
