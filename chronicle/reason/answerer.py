"""Answer via OpenAI-compatible endpoint. Never invent an answer from a document body."""
import json
import os
import urllib.request
from .models import AnswerResult, Evidence, QueryPlan

FALLBACK_CONTRACT = """Answer the question from the memory you built out of the corpus.
Rules:
1. Be short. Answer with the specific value asked for, not a paragraph.
2. Give the CURRENT state unless the question explicitly asks about the past. A later document may supersede an earlier one.
3. If the corpus does not support an answer, say plainly that it is not in the corpus. Never guess. Something only scheduled has not happened.
4. Cite the exact document ids you relied on.
Reply with a single JSON object and nothing else:
{"answer": "<your short answer>", "source_ids": ["<doc id>", ...]}"""

def _contract() -> str:
    try:
        from bench.answer_contract import ANSWER_CONTRACT
        return ANSWER_CONTRACT
    except ImportError:
        return FALLBACK_CONTRACT

def _extract_json(content: str) -> dict:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if start < 0 or end < start:
            raise ValueError("LLM returned no JSON object")
        return json.loads(content[start:end + 1])

def generate_answer(plan: QueryPlan, evidence: list[Evidence]) -> AnswerResult:
    if not evidence:
        return AnswerResult("Not in the corpus", [])
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("NEBIUS_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
    model = os.environ.get("MNEMO_MODEL") or os.environ.get("CHRONICLE_MODEL")
    if not model or not api_key:
        # Fail closed: the adapter is not an extractive QA engine.
        raise RuntimeError("Set MNEMO_MODEL (or CHRONICLE_MODEL) and OPENAI_API_KEY (or NEBIUS_API_KEY) to answer with the model")
    context = "\n\n".join(f"[{e.doc_id}] date={e.date}\n{e.text}" for e in evidence)
    payload = {"model": model, "messages": [
        {"role": "system", "content": _contract()},
        {"role": "user", "content": f"EVIDENCE:\n{context}\n\nQUESTION: {plan.question}"},
    ], "temperature": 0, "max_tokens": 600}
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.load(response)
    parsed = _extract_json(body["choices"][0]["message"]["content"])
    allowed = {e.doc_id for e in evidence}
    ids = parsed.get("source_ids") or []
    if not isinstance(ids, list):
        ids = []
    ids = list(dict.fromkeys(i for i in ids if isinstance(i, str) and i in allowed))
    answer = parsed.get("answer", "Not in the corpus")
    if not isinstance(answer, str):
        answer = "Not in the corpus"
    return AnswerResult(answer=answer, source_ids=ids)
