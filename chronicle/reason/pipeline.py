from pathlib import Path
from datetime import date
from chronicle.memory import MemoryAPI
from .planner import plan_query
from .retriever import retrieve
from .abstention import should_abstain
from .answerer import generate_answer
from .models import AnswerResult

def answer_question(question: str, state: str | Path | MemoryAPI, *, as_of: date | None = None) -> AnswerResult:
    plan = plan_query(question, as_of=as_of)
    evidence = retrieve(plan, state)
    if should_abstain(evidence):
        return AnswerResult("Not in the corpus", [])
    return generate_answer(plan, evidence)
