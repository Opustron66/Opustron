"""Composable ingestion pipeline and the incremental, idempotent corpus runner."""

import json
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from chronicle.schema import Claim, Document, Event

from .cache import DiskCache
from .entity_resolver import EntityResolver, resolve
from .extractor import LLM, ClaimExtractor, extract_entities, render_for_llm
from .parsers.benchmark import iter_documents
from .reconcile import ReconcileIndex
from .roster import load_or_build_roster

CLAIMS_FILE = "claims.jsonl"
DONE_FILE = "ingested_docs.json"
# Source text of every document, so the answer phase (which only gets --state) can quote it.
DOCS_FILE = "docs.jsonl"


class IngestPipeline:
    def process(self, events: Iterable[Event]) -> list[Event]:
        """Extract and resolve entities for each incoming event."""
        processed = []
        for event in events:
            event.entities = resolve(extract_entities(event))
            processed.append(event)
        return processed


@dataclass
class IngestStats:
    documents: int = 0
    skipped: int = 0
    claims: int = 0
    closings: int = 0
    failed: int = 0
    dropped: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    dropped_by_reason: dict[str, int] = field(default_factory=dict)


def read_claims(path: Path) -> list[Claim]:
    if not path.is_file():
        return []
    return [Claim.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_docs(path: Path) -> list[dict]:
    """Rows of ``docs.jsonl``: doc_id, date, kind, part, text (header + body, mentions resolved)."""
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_docs(path: Path, docs: list[Document], roster) -> None:
    """Append any document not yet in ``docs.jsonl``. Written for every doc, extraction or not."""
    have = {row["doc_id"] for row in read_docs(path)}
    with path.open("a", encoding="utf-8") as out:
        for doc in docs:
            if doc.doc_id in have:
                continue
            have.add(doc.doc_id)
            out.write(json.dumps({
                "doc_id": doc.doc_id,
                "date": doc.doc_date.isoformat() if doc.doc_date else None,
                "kind": doc.kind,
                "part": doc.part,
                "text": render_for_llm(doc, roster, known_people=False),
            }, ensure_ascii=False) + "\n")


def _drop_inverted(claims: list[Claim], extractor: ClaimExtractor) -> list[Claim]:
    """Drop claims that end before they start, counting them under "interval"."""
    kept = []
    for c in claims:
        if c.valid_from is not None and c.valid_to is not None and c.valid_to < c.valid_from:
            extractor.dropped["interval"] += 1
        else:
            kept.append(c)
    return kept


def run_ingest(documents: Iterable[Document], state: Path, llm: LLM, *, model: str = "nemotron",
               cache_dir: Path | None = None, workers: int = 6) -> IngestStats:
    """Extract claims for each not-yet-ingested document and append them to ``state/claims.jsonl``.

    Idempotent: re-running skips finished doc_ids; the LLM cache makes even forced re-runs free.
    A document that fails extraction is logged and does not abort the run (or get marked done).

    New in v3:
    - A Roster is built from *all* documents (including already-done ones) so the LLM
      always sees the full set of known people and Slack id→name mappings.
    - A ReconcileIndex tracks open stateful claims and emits closing claims when they
      are superseded, so P2 has closed intervals to query against.
    """
    state.mkdir(parents=True, exist_ok=True)
    claims_path, done_path = state / CLAIMS_FILE, state / DONE_FILE
    done = set(json.loads(done_path.read_text())) if done_path.is_file() else set()
    cache = DiskCache(cache_dir or state / ".llm_cache")

    # Materialise document list once (needed both for roster pre-pass and extraction)
    all_docs = list(documents)

    # Build / update the roster from all docs (pre-pass, cheap — no LLM)
    roster = load_or_build_roster(state, all_docs)
    _write_docs(state / DOCS_FILE, all_docs, roster)

    extractor = ClaimExtractor(llm, model=model, cache=cache, roster=roster)

    # Resolver seeded from existing claims for canonical name stability
    resolver = EntityResolver(aliases=roster.aliases)
    existing = read_claims(claims_path)
    for c in existing:
        resolver.resolve(c.subject)

    # Reconcile index seeded from existing claims for cross-part closing
    reconciler = ReconcileIndex()
    reconciler.extend(existing)

    stats = IngestStats()
    pending = []
    for doc in all_docs:
        if doc.doc_id in done:
            stats.skipped += 1
        else:
            pending.append(doc)

    def extract(doc: Document):
        try:
            return extractor.extract(doc), None
        except Exception as exc:  # noqa: BLE001
            return None, exc

    # Extraction (network-bound) runs in parallel; results are consumed in document order so
    # entity resolution and reconciliation stay deterministic.
    with claims_path.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for doc, (extracted, exc) in zip(pending, pool.map(extract, pending), strict=True):
            if exc is not None:
                stats.failed += 1
                print(f"[chronicle] FAILED {doc.doc_id}: {exc}", file=sys.stderr)
                continue
            resolved = [resolver.resolve_claim(c) for c in extracted]
            closings = reconciler.reconcile(resolved)
            resolved, closings = _drop_inverted(resolved, extractor), _drop_inverted(closings, extractor)
            for c in resolved + closings:
                out.write(c.model_dump_json() + "\n")
            out.flush()
            done.add(doc.doc_id)
            done_path.write_text(json.dumps(sorted(done)))
            stats.documents += 1
            stats.claims += len(resolved)
            stats.closings += len(closings)
    stats.dropped = extractor.dropped_total
    stats.dropped_by_reason = dict(extractor.dropped)
    stats.cache_hits, stats.cache_misses = cache.hits, cache.misses
    return stats


def ingest_corpus(corpus: Path, state: Path, llm: LLM, **kwargs) -> IngestStats:
    return run_ingest(iter_documents(corpus), state, llm, **kwargs)
