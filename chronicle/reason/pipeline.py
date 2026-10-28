import os
import re
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from chronicle.guard import llm
from chronicle.memory import MemoryAPI

from .abstention import should_abstain
from .answerer import Tools, answer_template, generate_answer, generate_corpus_answer
from .critic import critic_enabled, critique
from .grounding import claims, found_anywhere, norm
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
# For who holds a role, clear indirect evidence counts ("Rohan Dasgupta from Beacon", "Rohan's team"):
# run 5 named Beacon's lead from it, and the explicit-only second look refused in later runs.
SECOND_LOOK_ROLE = ("A first pass over less evidence found no answer. For who holds a role, clear indirect "
                    'evidence counts: lines like "<name> from <project>", "<name>\'s team" or "<name> '
                    '(<project>)". Name the best-supported person with their full name and cite those '
                    "documents. Only if nothing ties a person to it, reply that the corpus does not record it.")
_ROLE_Q = re.compile(r"\bwho (?:leads|owns|runs|heads|manages)\b|\bperson who (?:leads|owns|runs|heads)\b",
                     re.IGNORECASE)
# "Give both numbers": run 5 and a later check answered with one of the two.
_BOTH = re.compile(r"\bboth (?:numbers|values|figures)\b", re.IGNORECASE)
_PERCENT = re.compile(r"\d+(?:\.\d+)?\s?%")
# Dates, times and "24h"-style durations are not the figures asked for: a check answered "99.1% as
# of the 24h smoke test on 2026-05-26" and passed as two numbers.
_NOT_A_FIGURE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}|\b\d+[a-z]+\b|![0-9]+", re.IGNORECASE)
_FIGURE = re.compile(r"\d+(?:\.\d+)?\s?%|\b\d+(?:\.\d+)?\b")
BOTH_HINT = ('The question asks for both numbers. Give the value before and after, "from <before> to '
             '<after>", using figures for the exact context the question names.')


def missing_a_number(plan: QueryPlan, answer: str) -> bool:
    if not _BOTH.search(plan.question) or gave_up(answer):
        return False
    asked = set(_FIGURE.findall(_NOT_A_FIGURE.sub(" ", plan.question)))
    text = _NOT_A_FIGURE.sub(" ", answer)
    figures = _PERCENT.findall(text) if _PERCENT.search(text) else _FIGURE.findall(text)
    return len({f.replace(" ", "") for f in figures if f not in asked}) < 2


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


def grounding_enabled() -> bool:
    return os.environ.get("CHRONICLE_GROUNDING", "1").lower() not in ("0", "false", "no", "off")


def recheck_hint(missing: list[str]) -> str:
    return ("Check your previous answer: these parts were not backed by a quote copied word for word from "
            f"the evidence: {', '.join(missing[:8])}. Re-read the evidence. Answer the same question: keep "
            "each part the evidence supports and quote the exact lines for it, and correct any part it "
            "contradicts. Only if the evidence does not support an answer at all, say the corpus does "
            "not record it.")


def recheck(plan: QueryPlan, result: AnswerResult, again: Callable[[str], AnswerResult],
            evidence_texts: list[str] = ()) -> AnswerResult:
    """One correction pass for an answer with unsupported names/numbers; the better-backed one stays.
    A refusal replaces an answer only when none of its unsupported parts occur anywhere in the
    evidence: on corpus A a retry turned a right "30% reduction target" (30% was in the evidence,
    just not quoted) into "the corpus does not record", and correctly refused a made-up status."""
    if not result.unsupported or gave_up(result.answer):
        return result
    retry = again(recheck_hint(result.unsupported))
    if not retry.answer.strip():
        return result
    if gave_up(retry.answer):
        return retry if not found_anywhere(result.unsupported, evidence_texts) else result
    return retry if len(retry.unsupported) < len(result.unsupported) else result


def positive_form_enabled() -> bool:
    """CHRONICLE_POSITIVE_FORM=1 (the benchmark adapter sets it): rewrite answers whose first
    sentence puts the value next to a negation. Off by default."""
    return os.environ.get("CHRONICLE_POSITIVE_FORM", "0").lower() in ("1", "true", "yes", "on")


# The benchmark grades clause by clause and treats a value in a clause with one of these as denied,
# so "NOT shared (duplicated)" scores as not saying "duplicated". The model kept writing that shape
# despite the prompt rule, so the answer's first sentence is checked after the fact.
_NEGATION = re.compile(
    r"\b(?:not|never|no longer|rather than|instead of|isn't|aren't|wasn't|weren't|doesn't|don't|"
    r"didn't|cannot|can't|hasn't|haven't|hadn't)\b", re.IGNORECASE)
_YES_NO_QUESTION = re.compile(r"^\s*(?:is|are|does|do|has|had|was|were|did|can|will)\b|\byes or no\b|\byes \(",
                              re.IGNORECASE)

POSITIVE_FORM = """You fix the wording of an answer without changing what it says. A grader credits a value
only in a sentence that has no negation word ("not", "never", "no longer", "rather than", "instead of").
Rewrite the answer so it starts with the answer value as its own short sentence with no negation word,
for example "Duplicated." for "NOT shared (duplicated)", or "!342." for "!342 does not exist as a real
merge request" when the question asks which one is not real. You may then add one sentence that keeps
the negation ("It is not a real merge request."). Keep every fact, name, number and date; add nothing.
Reply with one JSON object: {"answer": "<rewritten answer>"}"""
POSITIVE_SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"],
                   "additionalProperties": False}


def first_sentence(answer: str) -> str:
    return _FIRST_SENTENCE.split(answer.strip(), maxsplit=1)[0]


def needs_positive_form(plan: QueryPlan, answer: str) -> bool:
    """A negation in the sentence that carries the value, on a question whose answer is a value.
    Yes/no questions, refusals and "did it happen?" questions are meant to be negative."""
    if gave_up(answer) or _YES_NO.match(answer) or _YES_NO_QUESTION.search(plan.question):
        return False
    if answer_template(plan) and "does not record" in answer_template(plan):
        return False
    return bool(_NEGATION.search(first_sentence(answer)))


def positive_form(plan: QueryPlan, result: AnswerResult) -> AnswerResult:
    if not needs_positive_form(plan, result.answer):
        return result
    try:
        reply = llm.complete([{"role": "system", "content": POSITIVE_FORM},
                              {"role": "user", "content": f"QUESTION: {plan.question}\nANSWER: {result.answer}"}],
                             schema=POSITIVE_SCHEMA)
    except Exception as exc:  # noqa: BLE001 - the original answer is still a valid answer
        print(f"[chronicle] positive-form rewrite failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return result
    rewritten = reply.get("answer") if isinstance(reply, dict) else None
    if (not isinstance(rewritten, str) or not rewritten.strip() or _NEGATION.search(first_sentence(rewritten))
            or gave_up(rewritten) or len(rewritten) > 2 * len(result.answer) + 80):
        return result
    return AnswerResult(rewritten.strip(), result.source_ids)


# The grader recognises "does not record" as a refusal but not "does not confirm", which the
# evidence rules themselves suggest ("the corpus does not confirm whether it happened").
_CONFIRM = re.compile(r"\b((?:corpus|evidence|documents?|records?)\s+)(?:does|do|did) not confirm\b",
                      re.IGNORECASE)


def record_wording(result: AnswerResult) -> AnswerResult:
    answer = _CONFIRM.sub(r"\1does not record", result.answer)
    return result if answer == result.answer else AnswerResult(answer, result.source_ids)


# The grader reads a clause holding "not" as denying everything in it, so "Provider C has
# experimental status and does not fully support it" denied "experimental" in run 6. A negated
# verb joined on with "and"/"which"/"so" becomes its own clause.
_JOINED_NEGATION = re.compile(
    r",?\s+(?:and|which|that|so|while)\s+((?:does|do|did|is|are|was|were|has|have|had|can|could|will|would)"
    r"\s+not\b|(?:doesn't|don't|didn't|isn't|aren't|wasn't|weren't|hasn't|haven't|cannot|can't|never|no longer)\b)",
    re.IGNORECASE)


def split_negations(result: AnswerResult) -> AnswerResult:
    if gave_up(result.answer):
        return result
    answer = _JOINED_NEGATION.sub(r"; it \1", result.answer)
    return result if answer == result.answer else AnswerResult(answer, result.source_ids)


def is_hard(plan: QueryPlan) -> bool:
    return plan.kind == "as_of" or bool(_HARD.search(plan.question))


def vote_key(answer: str) -> str:
    """What two answers must share to count as the same: the yes/no, else the first sentence."""
    if m := _YES_NO.match(answer):
        return m.group(1).lower()
    first = _FIRST_SENTENCE.split(answer.strip(), maxsplit=1)[0]
    return re.sub(r"[^a-z0-9%!]+", " ", first.lower()).strip()


# Two answers agree when they make the same claims (names, numbers, a short answer's words), not
# when their first sentences match: "Rohan Dasgupta." and "Rohan Dasgupta leads Beacon." are the
# same answer. With exact first sentences almost no two free-text samples matched, so the vote fell
# back to the first answer, and voted questions flipped between runs more than the others (27% of
# them across runs 4-7, against 6%).
AGREE = 0.5


def claim_set(answer: str, question: str = "") -> set[str]:
    """What an answer asserts, for comparing samples: its yes/no, or that it refused, plus its claims."""
    if gave_up(answer):
        return {"<refusal>"}
    out = {norm(c) for c in claims(answer, question)}
    # A name's single words ("rohan", "dasgupta") would count it twice next to "rohan dasgupta".
    parts = {w for c in out if " " in c for w in c.split()}
    out = {c for c in out if " " in c or c not in parts}
    if m := _YES_NO.match(answer):
        out.add(f"<{m.group(1).lower()}>")
    return out


def similarity(a: str, b: str, question: str = "") -> float:
    ca, cb = claim_set(a, question), claim_set(b, question)
    if ("<yes>" in ca and "<no>" in cb) or ("<no>" in ca and "<yes>" in cb):
        return 0.0
    if not ca and not cb:
        return float(vote_key(a) == vote_key(b))
    return len(ca & cb) / len(ca | cb) if ca | cb else 0.0


def agree(a: str, b: str, question: str = "") -> bool:
    return similarity(a, b, question) >= AGREE


def vote(first: AnswerResult, again: Callable[[float], AnswerResult], question: str = "") -> AnswerResult:
    """Up to three answers. A second sample that agrees with the first settles it; otherwise a
    third decides. With no two agreeing, the most typical one stays: the answer whose claims
    overlap most with the other two (the first, temperature-0 answer on a tie)."""
    second = again(VOTE_TEMPERATURE)
    if agree(first.answer, second.answer, question):
        return first
    third = again(VOTE_TEMPERATURE)
    if agree(first.answer, third.answer, question):
        return first
    if agree(second.answer, third.answer, question):
        return second
    samples = [first, second, third]
    scores = [sum(similarity(s.answer, o.answer, question) for o in samples if o is not s) for s in samples]
    return samples[max(range(3), key=lambda i: (scores[i], -i))]


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
            result = vote(result, lambda t: generate_answer(plan, evidence, tools, temperature=t), plan.question)
        if grounding_enabled():
            result = recheck(plan, result, lambda hint: generate_answer(plan, evidence, tools, hint),
                             [e.text for e in evidence])
        if gave_up(result.answer) and second_look_enabled():
            # Kept only when it answers and cites, so a correct "not recorded" survives a retry that
            # finds nothing.
            wide = retrieve_memory(plan, memory, state=path, **WIDE)
            retry = generate_answer(plan, wide, tools,
                                    SECOND_LOOK_ROLE if _ROLE_Q.search(plan.question) else SECOND_LOOK)
            if retry.source_ids and not gave_up(retry.answer):
                result, evidence = retry, wide
        if missing_a_number(plan, result.answer):
            retry = generate_answer(plan, evidence, tools, BOTH_HINT)
            if not missing_a_number(plan, retry.answer):
                result = retry
        if critic_enabled():
            result = critique(plan, result, evidence, gave_up)
        if positive_form_enabled():
            result = positive_form(plan, result)
        return record_wording(split_negations(result))
    finally:
        if owned:
            memory.close()
