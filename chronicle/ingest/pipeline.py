"""Composable ingestion pipeline and the incremental, idempotent corpus runner."""

import json
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from chronicle.schema import Claim, Document, Event

from .cache import DiskCache
from .entity_resolver import EntityResolver, resolve
from .extractor import LLM, ClaimExtractor, extract_entities
from .parsers.benchmark import iter_documents

CLAIMS_FILE = "claims.jsonl"
DONE_FILE = "ingested_docs.json"


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
    failed: int = 0
    dropped: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


def read_claims(path: Path) -> list[Claim]:
    if not path.is_file():
        return []
    return [Claim.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_ingest(documents: Iterable[Document], state: Path, llm: LLM, *, model: str = "nemotron",
               cache_dir: Path | None = None, workers: int = 6) -> IngestStats:
    """Extract claims for each not-yet-ingested document and append them to ``state/claims.jsonl``.

    Idempotent: re-running skips finished doc_ids; the LLM cache makes even forced re-runs free.
    A document that fails extraction is logged and does not abort the run (or get marked done).
    """
    state.mkdir(parents=True, exist_ok=True)
    claims_path, done_path = state / CLAIMS_FILE, state / DONE_FILE
    done = set(json.loads(done_path.read_text())) if done_path.is_file() else set()
    cache = DiskCache(cache_dir or state / ".llm_cache")
    extractor = ClaimExtractor(llm, model=model, cache=cache)
    resolver = EntityResolver()
    for c in read_claims(claims_path):  # keep canonical names consistent across part_a -> part_b
        resolver.resolve(c.subject)
    stats = IngestStats()
    pending = []
    for doc in documents:
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
    # entity resolution and claims.jsonl stay deterministic.
    with claims_path.open("a", encoding="utf-8") as out, ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for doc, (extracted, exc) in zip(pending, pool.map(extract, pending), strict=True):
            if exc is not None:
                stats.failed += 1
                print(f"[chronicle] FAILED {doc.doc_id}: {exc}", file=sys.stderr)
                continue
            for c in (resolver.resolve_claim(c) for c in extracted):
                out.write(c.model_dump_json() + "\n")
            out.flush()
            done.add(doc.doc_id)
            done_path.write_text(json.dumps(sorted(done)))
            stats.documents += 1
            stats.claims += len(extracted)
    stats.dropped, stats.cache_hits, stats.cache_misses = extractor.dropped, cache.hits, cache.misses
    return stats


def ingest_corpus(corpus: Path, state: Path, llm: LLM, **kwargs) -> IngestStats:
    return run_ingest(iter_documents(corpus), state, llm, **kwargs)
