"""A second model call that checks the draft answer against the question and the evidence.

Run 6 still lost answers that the evidence settled: a list missing one of the mitigations it
asked for, a refusal for "who leads Beacon" when the evidence names him, a deadline from the
first message of a thread that a later message moved. The critic reads the same evidence and
the draft, runs a short checklist, and may replace the draft only when it copies, word for word,
an evidence line that proves the problem. The code checks that quote really is in the evidence,
so a fix cannot rest on a line the model made up.
"""
import os
import sys

from chronicle.guard import llm

from .answerer import ANSWER_FORM, AS_OF_LATER, _render, answer_template, key_lines
from .grounding import norm
from .models import AnswerResult, Evidence, QueryPlan

CRITIC = """You check a draft answer to a question about a company's messages and documents, the way
a strict grader would. Check, in order:
1. Every part: the draft answers each part of the question (both people, both numbers, every
   item when asked to name them, the date and the agenda).
2. Exact context: figures and facts are for the exact thing the question names (that fixture,
   that person, that project, that date), not a similar one.
3. Latest: for a current-state question the value is the latest one. A later message in the same
   thread that moves a deadline or changes a plan supersedes the earlier one. With an as-of date,
   the value is the one that held on that date.
4. Roles: "who proposed" is the first person to suggest it; "who shipped" or "who implemented"
   is who did the work; "who leads" or "who owns" gives the person's full name when the evidence
   has it.
5. Refusals: a draft saying the corpus does not record something is wrong if the evidence
   states it.
6. Made-up status: a draft stating an outcome (merged, approved, completed, reviewed, ready) that
   the evidence does not state is wrong; then the corpus does not record that outcome.

Change the draft only for a problem you can prove with a line copied word for word from the
evidence. If the draft is right, or you are not sure, reply {"verdict": "ok"}. Otherwise reply
{"verdict": "fix", "problem": "<one sentence>", "quote": "<the evidence line, copied exactly>",
"answer": "<the corrected answer>", "source_ids": ["<doc id>", ...]}.
Keep everything the draft got right. The corrected answer follows these rules:

"""

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "fix"]},
        "problem": {"type": "string"},
        "quote": {"type": "string"},
        "answer": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict"],
    "additionalProperties": False,
}
MIN_QUOTE = 12


def critic_enabled() -> bool:
    """CHRONICLE_CRITIC=1 (the benchmark adapter sets it): check every answer once more.
    Off by default so UI chat stays cheaper."""
    return os.environ.get("CHRONICLE_CRITIC", "0").lower() in ("1", "true", "yes", "on")


def critic_messages(plan: QueryPlan, evidence: list[Evidence], draft: AnswerResult) -> list[dict]:
    system = CRITIC + ANSWER_FORM
    if template := answer_template(plan):
        system += f"\n\n{template}"
    reference = ""
    if plan.reference_date:
        reference = (f"The question is as of {plan.reference_date.isoformat()}. Documents marked WRITTEN "
                     f"AFTER THE AS-OF DATE: {AS_OF_LATER}\n\n")
    context = "\n\n".join(_render(e) for e in evidence)
    lines = key_lines(plan.question, evidence)
    focus = ("\n\nEvidence lines that repeat the question's own wording:\n" + "\n".join(f"- {x}" for x in lines)
             if lines else "")
    user = (f"{reference}EVIDENCE:\n{context}{focus}\n\nQUESTION: {plan.question}\n\n"
            f"DRAFT ANSWER: {draft.answer}\nDRAFT SOURCES: {', '.join(draft.source_ids) or '(none)'}")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def accept(plan: QueryPlan, draft: AnswerResult, reply, evidence: list[Evidence],
           gave_up=lambda answer: False) -> AnswerResult:
    """The critic's fix if it is well formed and proven by a verbatim evidence quote, else the draft.
    A fix that refuses replaces an answer only when the grounding check had flagged that answer."""
    if not isinstance(reply, dict) or reply.get("verdict") != "fix":
        return draft
    answer, quote = reply.get("answer"), reply.get("quote")
    if not isinstance(answer, str) or not answer.strip() or not isinstance(quote, str):
        return draft
    haystack = norm("\n".join(t for e in evidence for t in (e.text, _render(e))))
    if len(norm(quote)) < MIN_QUOTE or norm(quote) not in haystack:
        return draft
    if gave_up(answer) and not gave_up(draft.answer) and not draft.unsupported:
        return draft
    allowed = {e.doc_id for e in evidence} | {d for e in evidence for d in e.cites}
    ids = reply.get("source_ids") if isinstance(reply.get("source_ids"), list) else []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed)) or draft.source_ids
    return AnswerResult(answer.strip(), ids)


def critique(plan: QueryPlan, draft: AnswerResult, evidence: list[Evidence],
             gave_up=lambda answer: False) -> AnswerResult:
    if not evidence or not draft.answer.strip():
        return draft
    try:
        reply = llm.complete(critic_messages(plan, evidence, draft), schema=SCHEMA)
    except Exception as exc:  # noqa: BLE001 - the draft is still a valid answer
        print(f"[chronicle] critic failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return draft
    return accept(plan, draft, reply, evidence, gave_up)
