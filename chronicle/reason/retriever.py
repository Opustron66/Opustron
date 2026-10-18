"""Shared P2 temporal retrieval for UI chat and the benchmark adapter."""
import json
from pathlib import Path

from chronicle.memory import MemoryAPI
from chronicle.memory.api import CLAIMS_FILE, DB_FILE

from .models import Evidence, QueryPlan
from .planner import lexical_query


def retrieve_memory(plan: QueryPlan, memory: MemoryAPI, top_k: int = 8) -> list[Evidence]:
    """Use P2's temporal search, retaining each source citation."""
    results: dict[str, Evidence] = {}
    for hit in memory.search(lexical_query(plan.question), as_of=plan.reference_date, k=top_k, kind="claim"):
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


def retrieve(plan: QueryPlan, state: str | Path | MemoryAPI, top_k: int = 8) -> list[Evidence]:
    """Search an existing memory or sync/open/close the adapter's persistent state."""
    if isinstance(state, MemoryAPI):
        return retrieve_memory(plan, state, top_k)
    state = Path(state)
    if not (state / CLAIMS_FILE).is_file() and not (state / DB_FILE).is_file():
        raise FileNotFoundError(
            f"Ingest corpus with python -m chronicle.ingest before answering: {state / CLAIMS_FILE}. "
            "Legacy chronicle_adapter.sqlite3 state must be re-ingested."
        )
    with MemoryAPI.from_state(state) as memory:
        return retrieve_memory(plan, memory, top_k)
