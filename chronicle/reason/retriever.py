"""Shared P2 temporal retrieval for UI chat and the benchmark adapter.

Hybrid and time-aware: four channels are searched and fused with reciprocal rank fusion,
then packed into a character budget.

* claims: BM25 over P2's facts (``kind="claim"``), one evidence item per source document;
* topics: P1's consolidated timelines (``kind="topic"``), cut at the as-of date;
* entities: P1's person pages;
* documents: BM25 over the raw text of ``docs.jsonl``, so a value the extractor missed is
  still found.

Routing by question kind: an as-of question only sees facts true then, statements made by then,
and documents written by then. History and ordering questions see everything, timelines first.
"""
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from chronicle.memory import MemoryAPI
from chronicle.memory.api import CLAIMS_FILE, DB_FILE
from chronicle.memory.search import Chunk, chunk_documents, rank_chunks, rrf

from .models import Evidence, QueryPlan
from .planner import lexical_query

DOCS_FILE = "docs.jsonl"
CLAIM_K, TOPIC_K, ENTITY_K, CHUNK_K = 25, 6, 2, 16
# About 10k tokens of evidence: at 7k, questions that list every instance of something ("how many
# security reviews") saw only one of them.
CHAR_BUDGET = 40_000
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


def search_query(plan: QueryPlan) -> str:
    return " ".join([lexical_query(plan.question), *plan.terms])


def _as_of(plan: QueryPlan) -> date | None:
    return plan.reference_date if plan.kind == "as_of" else None


def retrieve_pages(plan: QueryPlan, memory: MemoryAPI, kind: str, k: int) -> list[Evidence]:
    """Topic timelines or entity pages from P1's consolidation, as one evidence item each."""
    out = []
    ref = _as_of(plan)
    for hit in memory.search(search_query(plan), as_of=ref, k=k, kind=kind):
        fact = hit.fact
        text = page_as_of(fact.content, ref) if kind == "topic" else fact.content
        if not text:
            continue
        cites = list(dict.fromkeys(s.doc_id for s in fact.sources))
        latest = max((s.observed_at for s in fact.sources if s.observed_at), default=None)
        out.append(Evidence(cites[-1] if cites else fact.fact_id, text,
                            latest.isoformat() if latest else "", hit.score, kind=kind, cites=cites))
    return out


def _day(value) -> str:
    return value.isoformat()[:10] if value is not None else ""


def fact_line(claim: dict, doc_id: str) -> str:
    """Zep-style: the fact with its validity interval, so the model sees when it held."""
    start = claim.get("valid_from") or "?"
    end = claim.get("valid_to") or "now"
    stated = claim.get("observed_at") or "?"
    predicate = claim["predicate"].replace("_", " ")
    return (f"FACT [{doc_id}] (valid {start} -> {end}; stated {stated}): "
            f"{claim['subject']} {predicate} {claim['object']} | \"{claim['quote']}\"")


def retrieve_claims(plan: QueryPlan, memory: MemoryAPI, top_k: int = CLAIM_K) -> list[Evidence]:
    """P2's temporal search; each source document becomes one evidence item of FACT lines.
    For as-of questions, statements made after the reference date are left out too."""
    ref = _as_of(plan)
    results: dict[str, Evidence] = {}
    for hit in memory.search(search_query(plan), as_of=ref, k=top_k, kind="claim"):
        fact = hit.fact
        for source in fact.sources:
            if ref is not None and source.observed_at is not None and _day(source.observed_at) > ref.isoformat():
                continue
            claim = fact.to_claim().model_dump(mode="json")
            claim.update(quote=source.quote, observed_at=_day(source.observed_at) or None)
            line = fact_line(claim, source.doc_id)
            if source.doc_id in results:
                evidence = results[source.doc_id]
                if line not in evidence.text:
                    evidence.text += "\n" + line
                evidence.score = max(evidence.score, hit.score)
            else:
                results[source.doc_id] = Evidence(source.doc_id, line, claim["observed_at"] or "", hit.score)
    return sorted(results.values(), key=lambda e: e.score, reverse=True)


@lru_cache(maxsize=4)
def _chunks(path: str, mtime: float) -> tuple[Chunk, ...]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return tuple(chunk_documents(rows))


def load_chunks(state: Path | None) -> list[Chunk]:
    if state is None:
        return []
    path = state / DOCS_FILE
    if not path.is_file():
        return []
    return list(_chunks(str(path), path.stat().st_mtime))


def retrieve_chunks(plan: QueryPlan, chunks: list[Chunk], k: int = CHUNK_K) -> list[Evidence]:
    return [Evidence(c.doc_id, c.text, c.date or "", score, kind="chunk")
            for c, score in rank_chunks(chunks, search_query(plan), k=k, until=_as_of(plan))]


def _key(e: Evidence) -> str:
    return f"{e.kind}|{e.doc_id}|{e.text[:80]}"


SECTION_ORDER = {"topic": 0, "entity": 1, "claim": 2, "chunk": 3, "later": 4}


def fuse(channels: list[list[Evidence]], budget: int = CHAR_BUDGET) -> list[Evidence]:
    """RRF over the channels, keep the best items that fit ``budget`` characters, then order
    them by section (timelines, person pages, facts, document excerpts) and fused score."""
    items: dict[str, Evidence] = {}
    for channel in channels:
        for e in channel:
            items.setdefault(_key(e), e)
    fused = rrf([[_key(e) for e in channel] for channel in channels])
    chosen, used = [], 0
    for key in sorted(fused, key=fused.get, reverse=True):
        e = items[key]
        if used + len(e.text) > budget:
            continue
        chosen.append(e)
        used += len(e.text)
        e.score = fused[key]
    return sorted(chosen, key=lambda e: (SECTION_ORDER.get(e.kind, 9), -e.score))


LATER_K = 4
LATER_BUDGET = 4_000


def retrieve_later(plan: QueryPlan, chunks: list[Chunk]) -> list[Evidence]:
    """For an as-of question, a few documents written after the as-of date, in their own section.

    Everything else is cut at the date, so "had Beacon reached 50% by 2026-05-10?" saw nothing
    about the milestone and answered "not recorded" instead of "no, it reached 50% on 05-14"."""
    ref = _as_of(plan)
    if ref is None:
        return []
    ranked = rank_chunks(chunks, search_query(plan), k=LATER_K * 5)
    later = [(c, s) for c, s in ranked if (c.date or "")[:10] > ref.isoformat()][:LATER_K]
    return [Evidence(c.doc_id, c.text, c.date or "", s, kind="later") for c, s in later]


def retrieve_memory(plan: QueryPlan, memory: MemoryAPI, top_k: int = CLAIM_K,
                    state: Path | None = None, *, budget: int = CHAR_BUDGET,
                    chunk_k: int = CHUNK_K, topic_k: int = TOPIC_K) -> list[Evidence]:
    if state is None and memory.database.path != ":memory:":
        state = Path(memory.database.path).parent
    chunks = load_chunks(state)
    channels = [
        retrieve_pages(plan, memory, "topic", topic_k),
        retrieve_pages(plan, memory, "entity", ENTITY_K),
        retrieve_claims(plan, memory, top_k),
        retrieve_chunks(plan, chunks, chunk_k),
    ]
    return fuse(channels, budget=budget) + fuse([retrieve_later(plan, chunks)], budget=LATER_BUDGET)


# The second look: when the first answer found nothing, about 25k tokens of evidence instead of 10k.
WIDE = {"top_k": 60, "budget": 100_000, "chunk_k": 40, "topic_k": 12}


SEARCH_BUDGET = 10_000


def search_more(plan: QueryPlan, memory: MemoryAPI, queries: list[str], state: Path | None = None) -> list[Evidence]:
    """The agentic answerer's ``search`` tool: the same channels and time routing as the first
    retrieval, for new keyword queries, in a smaller budget."""
    if state is None and memory.database.path != ":memory:":
        state = Path(memory.database.path).parent
    chunks = load_chunks(state)
    channels = []
    for query in queries:
        sub = QueryPlan(question=query, kind=plan.kind, reference_date=plan.reference_date)
        channels += [retrieve_pages(sub, memory, "topic", 3), retrieve_claims(sub, memory, 10),
                     retrieve_chunks(sub, chunks, 6)]
    return fuse(channels, budget=SEARCH_BUDGET)


def open_documents(plan: QueryPlan, memory: MemoryAPI, doc_ids: list[str], state: Path | None = None) -> list[Evidence]:
    """The ``open`` tool: full text of named documents (written by the as-of date, if any)."""
    if state is None and memory.database.path != ":memory:":
        state = Path(memory.database.path).parent
    path = state / DOCS_FILE if state is not None else None
    if path is None or not path.is_file():
        return []
    ref = _as_of(plan)
    wanted = set(doc_ids)
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["doc_id"] in wanted and (ref is None or (row.get("date") or "") <= ref.isoformat()):
            out.append(Evidence(row["doc_id"], row["text"], row.get("date") or "", 0.0, kind="chunk"))
    return out


def corpus_evidence(state: Path | None) -> list[Evidence]:
    """Every source document, oldest first, for whole-corpus answering. Not cut at an as-of date:
    the corpus is the same prefix for every question, so the provider can cache it."""
    path = state / DOCS_FILE if state is not None else None
    if path is None or not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda r: (r.get("date") or "", r["doc_id"]))
    return [Evidence(r["doc_id"], r["text"], r.get("date") or "", 0.0, kind="chunk") for r in rows]


def open_state(state: str | Path) -> MemoryAPI:
    """Sync and open the adapter's persistent state (the caller closes it)."""
    state = Path(state)
    if not (state / CLAIMS_FILE).is_file() and not (state / DB_FILE).is_file():
        raise FileNotFoundError(
            f"Ingest corpus with python -m chronicle.ingest before answering: {state / CLAIMS_FILE}. "
            "Legacy chronicle_adapter.sqlite3 state must be re-ingested."
        )
    return MemoryAPI.from_state(state)


def retrieve(plan: QueryPlan, state: str | Path | MemoryAPI, top_k: int = CLAIM_K) -> list[Evidence]:
    """Search an existing memory or sync/open/close the adapter's persistent state."""
    if isinstance(state, MemoryAPI):
        return retrieve_memory(plan, state, top_k)
    with open_state(state) as memory:
        return retrieve_memory(plan, memory, top_k, state=Path(state))
