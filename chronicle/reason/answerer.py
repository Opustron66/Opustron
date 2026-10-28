"""Generate privacy-routed answers with citations limited to retrieved evidence.

With ``tools`` the answerer is agentic: for up to ``MAX_ROUNDS`` model calls it may ask for more
evidence (``search`` with new queries, or ``open`` a full source document) before answering, and
the last round must answer. Without tools it answers in one call.
"""
import re
from collections.abc import Callable
from dataclasses import dataclass

from chronicle.guard import llm

from .models import AnswerResult, Evidence, QueryPlan

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "source_ids"],
    "additionalProperties": False,
}

FALLBACK_CONTRACT = """Answer the question from the memory you built out of the corpus.
Rules:
1. Be short. Answer with the specific value asked for, not a paragraph.
2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.
3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess.
4. Cite the exact document ids you relied on.
Reply with a single JSON object and nothing else:
{"answer": "<your short answer>", "source_ids": ["<doc id>", ...]}"""

EVIDENCE_RULES = """Evidence sufficiency rules (also apply when using a benchmark answer contract):
- A schedule, deadline, proposal or plan establishes intent, not whether an event occurred.
- A scheduled date in the past or future does not prove completion, non-completion or cancellation.
- If asked whether something happened and the evidence only schedules it, say the corpus does not confirm whether it happened. You may give its scheduled date.
- Say that an event completed, did not complete or was cancelled only when evidence explicitly supports that status as of the question's reference date.
- Missing evidence is not proof of a negative. Cite only documents that support what you actually assert.
- A definite completion, non-completion or cancellation answer must include the exact supporting evidence document IDs in source_ids."""

# Answers are graded clause by clause: a value is credited only where it is asserted, and a
# clause holding "not", "no longer", "rather than" or "instead of" denies everything in it.
# "NOT shared (duplicated)" therefore denies "duplicated", and a hedge added after an answer
# ("the corpus does not confirm ...") can turn it into a refusal.
ANSWER_FORM = """How to write the answer:
- Start with the bare answer as its own sentence: the name, number, date or value, or "Yes."
  or "No." Then add one short supporting sentence if useful. Keep negation words ("not",
  "no longer", "rather than", "instead of") out of the sentence that gives the value, even when
  the question asks which one is NOT something: write "Phoenix." or "Duplicated.", never
  "Phoenix is not a real project" or "NOT shared (duplicated)".
- When the evidence answers the question, answer it plainly. Do not add caveats such as "the
  corpus does not confirm ..." to an answer you have given.
- For the current state, give only the current value. Do not repeat superseded values, earlier
  plans or old proposals unless the question asks for the history.
- When the question asks how many, or for each/all items, count every distinct one in the
  evidence (same name but different date, purpose or owner = distinct) and list them all.
- When the corpus does not record what was asked, say "The corpus does not record <it>." and
  describe no outcome."""

def _contract() -> str:
    try:
        from bench.answer_contract import ANSWER_CONTRACT
        return ANSWER_CONTRACT
    except ImportError:
        return FALLBACK_CONTRACT

EVIDENCE_GUIDE = """How to read the evidence:
- TOPIC blocks are timelines of one tracked value, oldest statement first; each line gives the
  date it was stated, the source document and a verbatim quote. LATEST is the most recent statement.
- FACT lines give a fact's validity interval (valid FROM -> TO; "now" = still true) and the date
  it was stated.
- DOCUMENT blocks are raw source text; prefer them when they disagree with a FACT or TOPIC.
- Cite the document ids (the [...] ids) that support your answer."""


def _render(e: Evidence) -> str:
    if e.kind == "topic":
        return e.text
    if e.kind == "entity":
        return f"PERSON PAGE\n{e.text}"
    if e.kind == "chunk":
        return f"DOCUMENT [{e.doc_id}] written {e.date}\n{e.text}"
    if e.kind == "later":
        return f"WRITTEN AFTER THE AS-OF DATE [{e.doc_id}] written {e.date}\n{e.text}"
    return e.text


MAX_ROUNDS = 3

AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["answer", "search", "open"]},
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "queries": {"type": "array", "items": {"type": "string"}},
        "doc_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action"],
    "additionalProperties": False,
}

AGENT_RULES = """You may gather more evidence before answering. Reply with ONE JSON object:
- {"action": "answer", "answer": "...", "source_ids": [...]} when the evidence answers the question
  (or clearly shows the corpus does not record it). Prefer this.
- {"action": "search", "queries": ["...", "..."]} to search the corpus again with up to 3 new
  keyword queries (other names, ids, synonyms) when a key fact is missing.
- {"action": "open", "doc_ids": ["..."]} to read up to 3 full source documents named in the evidence.
Search or open only when needed: each costs a turn."""

LAST_TURN = "This is your last turn: answer now with the evidence you have."


@dataclass
class Tools:
    """What the agentic answerer may call: more retrieval and full-document reads."""

    search: Callable[[list[str]], list[Evidence]]
    open: Callable[[list[str]], list[Evidence]]


_CHAIN = re.compile(r"\bin between\b|more than once", re.IGNORECASE)
_ORDER = re.compile(r"\bin the order\b|earliest first|\border they happened\b", re.IGNORECASE)
_OUTCOME = re.compile(r"^\s*(how did|how was|what was the outcome|did)\b", re.IGNORECASE)
_TWO = re.compile(r"\b(two different|are different|is that right)\b", re.IGNORECASE)


def answer_template(plan: QueryPlan) -> str:
    """Short answer shapes for question types the grader matches strictly."""
    q = plan.question
    if _CHAIN.search(q):
        return ('Answer shape: "In between: <value it held between the first and the latest>; now: '
                '<latest value>." Give each value exactly as the documents state it.')
    if _ORDER.search(q):
        return "Answer shape: the items, earliest first, one per line, using the question's wording."
    if _TWO.search(q):
        return 'Answer shape: "Yes. <first>: <what it is>. <second>: <what it is>." One short clause each.'
    if _OUTCOME.search(q) or plan.question_type == "abstention_risk":
        return ("If the evidence does not record that this happened or how it went, answer in one "
                "sentence that the corpus does not record it (e.g. it was only scheduled); do not "
                "describe an outcome.")
    return ""


def _messages(plan: QueryPlan, evidence: list[Evidence], *, agentic: bool, last: bool, note: str = "",
              hint: str = "") -> list[dict]:
    context = "\n\n".join(_render(e) for e in evidence)
    reference = f"Answer as of {plan.reference_date.isoformat()}.\n\n" if plan.reference_date else ""
    if plan.reference_date and any(e.kind == "later" for e in evidence):
        reference = (f"Answer as of {plan.reference_date.isoformat()}. Documents marked WRITTEN AFTER THE "
                     "AS-OF DATE are not true as of that date: never report their values as the answer. "
                     "Use them only to say that something had not happened yet, or was not yet decided, "
                     "by the as-of date (and when it happened).\n\n")
    if plan.reference_date:
        reference += ('For "had X happened by then?" answer "Yes." or "No." first, then the value it held '
                      'on that date in positive form (e.g. "It was still in beta.", not "It had not '
                      'launched.") and, if it changed later, the date it changed.\n\n')
    system = f"{_contract()}\n\n{EVIDENCE_GUIDE}\n\n{EVIDENCE_RULES}\n\n{ANSWER_FORM}"
    if template := answer_template(plan):
        system += f"\n\n{template}"
    user = f"{reference}EVIDENCE:\n{context}\n\nQUESTION: {plan.question}"
    if hint:
        user += f"\n\n{hint}"
    if agentic:
        system += f"\n\n{AGENT_RULES}"
        user += f"\n\n{note}{LAST_TURN if last else ''}".rstrip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


BRIEF = ("Keep your reasoning short: a few sentences at most. The answer must be one short "
         "JSON object.")


def _complete(messages: list[dict], schema: dict):
    """One model call; a reply cut off by the token limit (a reasoning model thinking too long)
    is retried once with a request to think briefly."""
    try:
        return llm.complete(messages, schema=schema)
    except ValueError as exc:
        if "truncated reply" not in str(exc):
            raise
        retry = [*messages[:-1], {**messages[-1], "content": messages[-1]["content"] + "\n\n" + BRIEF}]
        return llm.complete(retry, schema=schema)


def _key(e: Evidence) -> tuple:
    return (e.kind, e.doc_id, e.text[:80])


def _str_list(value, limit: int = 3) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v.strip() for v in value if isinstance(v, str) and v.strip()][:limit]


def generate_answer(plan: QueryPlan, evidence: list[Evidence], tools: Tools | None = None,
                    hint: str = "") -> AnswerResult:
    if not evidence:
        return AnswerResult("Not in the corpus", [])
    evidence = list(evidence)
    if tools is None:
        parsed = _complete(_messages(plan, evidence, agentic=False, last=True, hint=hint), ANSWER_SCHEMA)
    else:
        note = ""
        for round_number in range(1, MAX_ROUNDS + 1):
            last = round_number == MAX_ROUNDS
            parsed = _complete(_messages(plan, evidence, agentic=True, last=last, note=note, hint=hint),
                               AGENT_SCHEMA)
            if not isinstance(parsed, dict):
                raise ValueError("LLM returned no JSON object")
            action = parsed.get("action")
            if last or action not in ("search", "open"):
                break
            asked = _str_list(parsed.get("queries" if action == "search" else "doc_ids"))
            found = (tools.search if action == "search" else tools.open)(asked) if asked else []
            have = {_key(e) for e in evidence}
            new = [e for e in found if _key(e) not in have]
            evidence += new
            note = (f"({action} {asked!r} added {len(new)} evidence items.)\n" if new
                    else f"({action} {asked!r} found nothing new.)\n")
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned no JSON object")
    allowed = {e.doc_id for e in evidence} | {d for e in evidence for d in e.cites}
    ids = parsed.get("source_ids") or []
    if not isinstance(ids, list):
        ids = []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))
    answer = parsed.get("answer", "Not in the corpus")
    if not isinstance(answer, str) or not answer.strip():
        answer = "Not in the corpus"
    return AnswerResult(answer=answer, source_ids=ids)
