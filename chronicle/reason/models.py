from dataclasses import dataclass, field
from datetime import date

@dataclass
class QueryPlan:
    question: str
    kind: str = "search"  # as_of | current | ordering_or_history | search
    reference_date: date | None = None
    # From the optional LLM query-understanding call: extra BM25 terms and its question type.
    terms: list[str] = field(default_factory=list)
    question_type: str = ""

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
