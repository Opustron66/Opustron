"""Keyword search over facts, with the same as-of filter as the temporal queries.

Ranking is BM25 over each fact's subject, predicate, object, content and source quotes, so a
question matches either the extracted triple or the words the document used. Ties go to the fact
that started later. Superseded facts are searchable (``as_of=None``) because questions like "who
owned payments before Dana?" need them; pass ``as_of`` to see only what held on that day.
"""

import math
import re
from collections import Counter
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


def rank(facts: list[Fact], query: str, *, k: int = 10) -> list[SearchHit]:
    terms = set(tokens(query))
    if not terms or not facts:
        return []
    docs = [Counter(tokens(fact_text(f))) for f in facts]
    avg_len = sum(sum(d.values()) for d in docs) / len(docs) or 1.0
    df = Counter(t for d in docs for t in terms if t in d)
    n = len(docs)
    hits = []
    for fact, doc in zip(facts, docs, strict=True):
        length = sum(doc.values())
        score = 0.0
        for term in terms & doc.keys():
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            tf = doc[term]
            score += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * length / avg_len))
        if score > 0:
            hits.append(SearchHit(fact, score))
    hits.sort(key=lambda h: (h.score, to_ts(h.fact.valid_from) or ""), reverse=True)
    return hits[:k]


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
