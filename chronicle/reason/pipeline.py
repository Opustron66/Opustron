import os
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

from chronicle.memory import MemoryAPI

from .abstention import should_abstain
from .answerer import Tools, generate_answer, generate_corpus_answer
from .models import AnswerResult, QueryPlan
from .planner import plan_query, understand
from .retriever import (
    WIDE,
    corpus_evidence,
    open_documents,
    open_state,
    retrieve_memory,
    search_more,
)


def agentic_enabled() -> bool:
    return os.environ.get("CHRONICLE_AGENTIC", "1").lower() not in ("0", "false", "no", "off")


def full_corpus_enabled() -> bool:
    """CHRONICLE_FULL_CORPUS=1: answer every question over the whole corpus instead of retrieved
    evidence. Off by default; for small corpora that fit the model's context."""
    return os.environ.get("CHRONICLE_FULL_CORPUS", "0").lower() in ("1", "true", "yes", "on")


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


def vote_enabled() -> bool:
    """CHRONICLE_VOTE=1 (the benchmark adapter sets it): answer hard questions up to three times.
    Off by default so UI chat stays one call per question."""
    return os.environ.get("CHRONICLE_VOTE", "0").lower() in ("1", "true", "yes", "on")


# Question shapes whose answers flipped between identical runs on corpus A (yes/no, "which one",
# "how many", as-of): these are answered again and the majority kept.
_HARD = re.compile(
    r"\banswer (?:with )?(?:yes|no|which)|\byes \(|\bhow many\b|\bwhich (?:one|of|are|is)\b"
    r"|^\s*of .{3,120}, which\b|\bas of \d{4}-\d{2}-\d{2}|\bboth numbers\b|\bfull name\b"
    r"|\bsame (?:system|person|thing)\b|\bsingle current state\b"
    r"|^\s*(?:is|are|does|do|has|had|was|were)\b", re.IGNORECASE)
VOTE_TEMPERATURE = 0.6
_YES_NO = re.compile(r"^\W*(yes|no)\b", re.IGNORECASE)
_FIRST_SENTENCE = re.compile(r"[.!?](?:\s|$)|\n")


def is_hard(plan: QueryPlan) -> bool:
    return plan.kind == "as_of" or bool(_HARD.search(plan.question))


def vote_key(answer: str) -> str:
    """What two answers must share to count as the same: the yes/no, else the first sentence."""
    if m := _YES_NO.match(answer):
        return m.group(1).lower()
    first = _FIRST_SENTENCE.split(answer.strip(), maxsplit=1)[0]
    return re.sub(r"[^a-z0-9%!]+", " ", first.lower()).strip()


def vote(first: AnswerResult, again: Callable[[float], AnswerResult]) -> AnswerResult:
    """Majority of up to three answers. A second sample that agrees with the first settles it;
    otherwise a third decides, and with no majority the first (temperature 0) answer stands."""
    second = again(VOTE_TEMPERATURE)
    if vote_key(second.answer) == vote_key(first.answer):
        return first
    third = again(VOTE_TEMPERATURE)
    if vote_key(third.answer) == vote_key(second.answer):
        return second
    return first


def answer_question(question: str, state: str | Path | MemoryAPI, *, as_of: date | None = None) -> AnswerResult:
    plan = understand(plan_query(question, as_of=as_of))
    owned = not isinstance(state, MemoryAPI)
    memory = open_state(state) if owned else state
    path = Path(state) if owned else None
    try:
        if full_corpus_enabled():
            if path is None and memory.database.path != ":memory:":
                path = Path(memory.database.path).parent
            return generate_corpus_answer(plan, corpus_evidence(path))
        evidence = retrieve_memory(plan, memory, state=path)
        if should_abstain(evidence):
            return AnswerResult("Not in the corpus", [])
        tools = Tools(search=lambda queries: search_more(plan, memory, queries, path),
                      open=lambda doc_ids: open_documents(plan, memory, doc_ids, path)) if agentic_enabled() else None
        result = generate_answer(plan, evidence, tools)
        if vote_enabled() and is_hard(plan):
            result = vote(result, lambda t: generate_answer(plan, evidence, tools, temperature=t))
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
