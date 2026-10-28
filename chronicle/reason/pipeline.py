import os
import re
from datetime import date
from pathlib import Path

from chronicle.memory import MemoryAPI

from .abstention import should_abstain
from .answerer import Tools, generate_answer
from .models import AnswerResult
from .planner import plan_query, understand
from .retriever import WIDE, open_documents, open_state, retrieve_memory, search_more


def agentic_enabled() -> bool:
    return os.environ.get("CHRONICLE_AGENTIC", "1").lower() not in ("0", "false", "no", "off")


def second_look_enabled() -> bool:
    return os.environ.get("CHRONICLE_SECOND_LOOK", "1").lower() not in ("0", "false", "no", "off")


# A first sentence that says the corpus is silent. Retrieval had missed the document in a third of
# these on corpus A ("who leads Beacon?" answered "the corpus does not record").
_GAVE_UP = re.compile(r"^[^.]*\b(?:does|do|did) not (?:record|contain|mention|state|confirm|specify|say)\b"
                      r"|^[^.]*\bnot in the corpus\b", re.IGNORECASE)

SECOND_LOOK = ("A first pass over less evidence found no answer. Answer only if this evidence states it "
               "explicitly, and cite that document. Otherwise reply that the corpus does not record it.")


def gave_up(answer: str) -> bool:
    return bool(_GAVE_UP.search(answer))


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
        result = generate_answer(plan, evidence, tools)
        if gave_up(result.answer) and second_look_enabled():
            # Kept only when it answers and cites, so a correct "not recorded" survives a retry that
            # finds nothing.
            retry = generate_answer(plan, retrieve_memory(plan, memory, state=path, **WIDE), tools, SECOND_LOOK)
            if retry.source_ids and not gave_up(retry.answer):
                return retry
        return result
    finally:
        if owned:
            memory.close()
