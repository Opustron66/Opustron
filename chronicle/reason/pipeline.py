from datetime import date
from .planner import plan_query
from .retriever import MemoryReader, MockMemoryReader, retrieve
from .abstention import has_unambiguous_support
from .answerer import abstain, format_answer

def answer_question(question: str, memory: MemoryReader | None = None, *, today: date | None = None) -> dict[str, object]:
    """Dependency-injected pipeline: easy to test and swap P2's memory."""
    reader = memory if memory is not None else MockMemoryReader()
    plan = plan_query(question)
    evidence = retrieve(plan, reader, today if today is not None else date.today())
    return format_answer(evidence) if has_unambiguous_support(evidence) else abstain()
