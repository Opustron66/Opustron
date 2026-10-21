"""Shared P2 temporal retrieval for UI chat and the benchmark adapter."""
import json
import re
from datetime import date
from pathlib import Path

from chronicle.memory import MemoryAPI
from chronicle.memory.api import CLAIMS_FILE, DB_FILE

from .models import Evidence, QueryPlan
from .planner import lexical_query


TOPIC_K, ENTITY_K = 4, 2
_ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}) \[[^\]]+\]: (.*?)(?: \(effective [^)]*\))? \| ")


def page_as_of(content: str, reference: date | None) -> str:
    """A topic timeline cut at ``reference``: entries stated later are dropped and the
    summary lines recomputed, so an as-of answer never sees what came after."""
    if reference is None or not content.startswith("TOPIC:"):
        return content
    lines = content.splitlines()
    kept, values = [lines[0]], []
    for line in lines[1:]:
        m = _ENTRY.match(line)
        if m and m.group(1) <= reference.isoformat():
            kept.append(line)
            values.append((m.group(1), m.group(2)))
    if not values:
        return ""
    ordered = list(dict.fromkeys(v for _, v in values))
    if len(ordered) > 1:
        kept.append("VALUES IN ORDER: " + " -> ".join(ordered))
    kept.append(f"LATEST ({values[-1][0]}): {values[-1][1]}")
    return "\n".join(kept)


def retrieve_pages(plan: QueryPlan, memory: MemoryAPI, kind: str, k: int) -> list[Evidence]:
    """Topic timelines or entity pages from P1's consolidation, as one evidence item each."""
    out = []
    for hit in memory.search(lexical_query(plan.question), as_of=plan.reference_date, k=k, kind=kind):
        fact = hit.fact
        text = page_as_of(fact.content, plan.reference_date) if kind == "topic" else fact.content
        if not text:
            continue
        cites = list(dict.fromkeys(s.doc_id for s in fact.sources))
        latest = max((s.observed_at for s in fact.sources if s.observed_at), default=None)
        out.append(Evidence(cites[-1] if cites else fact.fact_id, text,
                            latest.isoformat() if latest else "", hit.score, kind=kind, cites=cites))
    return out


def retrieve_memory(plan: QueryPlan, memory: MemoryAPI, top_k: int = 8) -> list[Evidence]:
    """Use P2's temporal search, retaining each source citation."""
    pages = retrieve_pages(plan, memory, "topic", TOPIC_K) + retrieve_pages(plan, memory, "entity", ENTITY_K)
    return pages + retrieve_claims(plan, memory, top_k)


def retrieve_claims(plan: QueryPlan, memory: MemoryAPI, top_k: int = 8) -> list[Evidence]:
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
