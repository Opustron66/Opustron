"""P2 temporal retrieval for UI chat and legacy claim retrieval for the benchmark."""
import json
import re
from pathlib import Path

from chronicle.ingest.pipeline import CLAIMS_FILE, read_claims
from chronicle.memory import MemoryAPI

from .models import Evidence, QueryPlan

STOPWORDS = set("a an the is are was were who what which when where why how did does do to in on at for from with of and or by it its this that currently current now".split())

def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOPWORDS}


def retrieve_memory(plan: QueryPlan, memory: MemoryAPI, top_k: int = 8) -> list[Evidence]:
    """Use P2's temporal search for UI questions, retaining each source citation."""
    results: dict[str, Evidence] = {}
    for hit in memory.search(plan.question, as_of=plan.reference_date, k=top_k, kind="claim"):
        fact = hit.fact
        for source in fact.sources:
            claim = fact.to_claim().model_dump(mode="json")
            claim.update(doc_id=source.doc_id, quote=source.quote,
                         observed_at=source.observed_at.isoformat() if source.observed_at else None)
            content = json.dumps(claim)
            observed = claim["observed_at"] or ""
            if source.doc_id in results:
                evidence = results[source.doc_id]
                evidence.text += "\n" + content
                evidence.score = max(evidence.score, hit.score)
            else:
                results[source.doc_id] = Evidence(source.doc_id, content, observed, hit.score)
    return sorted(results.values(), key=lambda e: e.score, reverse=True)[:top_k]

def retrieve(plan: QueryPlan, state: Path, top_k: int = 8) -> list[Evidence]:
    claims_path = state / CLAIMS_FILE
    if not claims_path.is_file():
        raise FileNotFoundError(
            f"Ingest corpus with python -m chronicle.ingest before answering: {claims_path}. "
            "Legacy chronicle_adapter.sqlite3 state must be re-ingested."
        )
    query_terms = terms(plan.question)
    results: dict[str, Evidence] = {}
    for claim in read_claims(claims_path):
        overlap = len(query_terms & terms(
            f"{claim.subject} {claim.predicate} {claim.object} {claim.quote}"
        ))
        if overlap:
            # Retain source quotes and validity fields, including closing claims.
            # P2 will supply supersession/as-of semantics; do not infer them here.
            content = claim.model_dump_json()
            observed = claim.observed_at.isoformat() if claim.observed_at else ""
            if claim.doc_id in results:
                evidence = results[claim.doc_id]
                evidence.text += "\n" + content
                evidence.date = max(evidence.date, observed)
                evidence.score = max(evidence.score, float(overlap))
            else:
                results[claim.doc_id] = Evidence(
                    doc_id=claim.doc_id, text=content, date=observed, score=float(overlap),
                )
    return sorted(results.values(), key=lambda e: (e.score, e.date), reverse=True)[:top_k]
