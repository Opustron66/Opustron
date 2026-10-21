import os
from datetime import date
from pathlib import Path

from chronicle.memory import MemoryAPI

from .abstention import should_abstain
from .answerer import Tools, generate_answer
from .models import AnswerResult
from .planner import plan_query, understand
from .retriever import open_documents, open_state, retrieve_memory, search_more


def agentic_enabled() -> bool:
    return os.environ.get("CHRONICLE_AGENTIC", "1").lower() not in ("0", "false", "no", "off")


def answer_question(question: str, state: str | Path | MemoryAPI, *, as_of: date | None = None) -> AnswerResult:
    plan = understand(plan_query(question, as_of=as_of))
    owned = not isinstance(state, MemoryAPI)
    memory = open_state(state) if owned else state
    path = Path(state) if owned else None
    try:
        evidence = retrieve_memory(plan, memory, state=path)
        if should_abstain(evidence):
            return AnswerResult("Not in the corpus", [])
        tools = Tools(search=lambda queries: search_more(plan, memory, queries, path),
                      open=lambda doc_ids: open_documents(plan, memory, doc_ids, path)) if agentic_enabled() else None
        return generate_answer(plan, evidence, tools)
    finally:
        if owned:
            memory.close()
