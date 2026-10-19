"""Generate privacy-routed answers with citations limited to retrieved evidence."""
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

def _contract() -> str:
    try:
        from bench.answer_contract import ANSWER_CONTRACT
        return ANSWER_CONTRACT
    except ImportError:
        return FALLBACK_CONTRACT

def generate_answer(plan: QueryPlan, evidence: list[Evidence]) -> AnswerResult:
    if not evidence:
        return AnswerResult("Not in the corpus", [])
    context = "\n\n".join(f"[{e.doc_id}] date={e.date}\n{e.text}" for e in evidence)
    reference = f"Answer as of {plan.reference_date.isoformat()}.\n\n" if plan.reference_date else ""
    messages = [
        {"role": "system", "content": f"{_contract()}\n\n{EVIDENCE_RULES}"},
        {"role": "user", "content": f"{reference}EVIDENCE:\n{context}\n\nQUESTION: {plan.question}"},
    ]
    parsed = llm.complete(messages, schema=ANSWER_SCHEMA)
    if not isinstance(parsed, dict):
        raise ValueError("LLM returned no JSON object")
    allowed = {e.doc_id for e in evidence}
    ids = parsed.get("source_ids") or []
    if not isinstance(ids, list):
        ids = []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))
    answer = parsed.get("answer", "Not in the corpus")
    if not isinstance(answer, str):
        answer = "Not in the corpus"
    return AnswerResult(answer=answer, source_ids=ids)
