"""Keyword search over facts, with the same as-of filter as the temporal queries.

Ranking is BM25 over each fact's subject, predicate, object, content and source quotes, so a
question matches either the extracted triple or the words the document used. Ties go to the fact
that started later. Superseded facts are searchable (``as_of=None``) because questions like "who
owned payments before Dana?" need them; pass ``as_of`` to see only what held on that day.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from .database import MemoryDatabase
from .models import Fact, SearchHit, to_ts
from .queries import all_facts
from .queries import as_of as facts_as_of

# Words under three letters are dropped anyway.
STOPWORDS = frozenset({
    "the", "are", "was", "were", "been", "who", "whom", "what", "which", "when", "where", "why",
    "how", "did", "does", "for", "from", "with", "and", "its", "this", "that", "these", "those",
    "currently", "current", "now", "then", "has", "have", "had", "about", "into", "over", "under",
    "not", "yes", "any", "all", "our", "your", "their", "his", "her", "them", "they", "she", "you",
})
_WORD = re.compile(r"[a-z0-9]+")
K1, B = 1.2, 0.75


def tokens(text: str) -> list[str]:
    """Lowercase words of 3+ characters, stopwords dropped, plural ``s`` stripped."""
    out = []
    for word in _WORD.findall(text.casefold()):
        if len(word) < 3 or word in STOPWORDS:
            continue
        if len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


def fact_text(fact: Fact) -> str:
    parts = [fact.subject, fact.predicate.replace("_", " "), fact.object, fact.content]
    parts += [s.quote for s in fact.sources]
    return " ".join(p for p in parts if p)


def bm25(texts: list[str], query: str) -> list[float]:
    """BM25 score of each text for ``query`` (0 where no term matches)."""
    terms = set(tokens(query))
    if not terms or not texts:
        return [0.0] * len(texts)
    docs = [Counter(tokens(t)) for t in texts]
    avg_len = sum(sum(d.values()) for d in docs) / len(docs) or 1.0
    df = Counter(t for d in docs for t in terms if t in d)
    n = len(docs)
    scores = []
    for doc in docs:
        length = sum(doc.values())
        score = 0.0
        for term in terms & doc.keys():
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            tf = doc[term]
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / avg_len))
        scores.append(score)
    return scores


def rank(facts: list[Fact], query: str, *, k: int = 10) -> list[SearchHit]:
    hits = [SearchHit(fact, score) for fact, score in zip(facts, bm25([fact_text(f) for f in facts], query),
                                                          strict=True) if score > 0]
    hits.sort(key=lambda h: (h.score, to_ts(h.fact.valid_from) or ""), reverse=True)
    return hits[:k]


@dataclass(slots=True)
class Chunk:
    """A piece of a source document (most corpus documents fit in one)."""

    doc_id: str
    date: str | None
    text: str


CHUNK_CHARS = 1600


def chunk_documents(rows: list[dict], max_chars: int = CHUNK_CHARS) -> list[Chunk]:
    """Split ``docs.jsonl`` rows into chunks of whole lines; every chunk of a document repeats
    its header line (Subject/Channel) so it can be matched on its own."""
    chunks = []
    for row in rows:
        text = row.get("text") or ""
        if len(text) <= max_chars:
            chunks.append(Chunk(row["doc_id"], row.get("date"), text))
            continue
        lines = text.splitlines()
        header, piece = lines[0], []
        for line in lines[1:]:
            if piece and sum(len(x) + 1 for x in piece) + len(line) > max_chars:
                chunks.append(Chunk(row["doc_id"], row.get("date"), "\n".join([header, *piece])))
                piece = []
            piece.append(line)
        if piece:
            chunks.append(Chunk(row["doc_id"], row.get("date"), "\n".join([header, *piece])))
    return chunks


def rank_chunks(chunks: list[Chunk], query: str, *, k: int = 10,
                until: date | None = None) -> list[tuple[Chunk, float]]:
    """BM25 over document chunks; ``until`` keeps only documents written on or before that day."""
    pool = [c for c in chunks if until is None or (c.date or "") <= until.isoformat()]
    scored = [(c, s) for c, s in zip(pool, bm25([c.text for c in pool], query), strict=True) if s > 0]
    scored.sort(key=lambda cs: (cs[1], cs[0].date or ""), reverse=True)
    return scored[:k]


def rrf(rankings: list[list[str]], *, k: int = 60) -> dict[str, float]:
    """Reciprocal rank fusion: each key scores sum(1 / (k + rank)) over the rankings it is in."""
    fused: dict[str, float] = {}
    for ranking in rankings:
        for position, key in enumerate(ranking, start=1):
            fused[key] = fused.get(key, 0.0) + 1.0 / (k + position)
    return fused


def search(db: MemoryDatabase, query: str, *, as_of: date | datetime | str | None = None,
           known_at: date | datetime | str | None = None, k: int = 10, kind: str | None = None) -> list[SearchHit]:
    pool = facts_as_of(db, as_of, known_at=known_at, kind=kind) if as_of is not None else \
        all_facts(db, known_at=known_at, kind=kind)
    return rank(pool, query, k=k)


class MemorySearch:
    def __init__(self, database: MemoryDatabase) -> None:
        self.database = database

    def search(self, query: str, **kwargs) -> list[SearchHit]:
        return search(self.database, query, **kwargs)
