"""Temporary SQLite document retriever. P2's temporal store will replace it."""
import re
import sqlite3
from pathlib import Path
from .models import Evidence, QueryPlan

STOPWORDS = set("a an the is are was were who what which when where why how did does do to in on at for from with of and or by it its this that currently current now".split())

def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOPWORDS}

def retrieve(plan: QueryPlan, state: Path, top_k: int = 8) -> list[Evidence]:
    db = state / "chronicle_adapter.sqlite3"
    if not db.exists():
        raise FileNotFoundError(f"Ingest corpus before answering: {db}")
    query_terms = terms(plan.question)
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT doc_id, doc_date, subject, body FROM documents").fetchall()
    results = []
    for doc_id, doc_date, subject, body in rows:
        content = f"{subject or ''} {body or ''}"
        doc_terms = terms(content)
        overlap = len(query_terms & doc_terms)
        if overlap:
            # Dates here are metadata, not validity intervals. Never pretend
            # document date alone establishes the correct historical state.
            results.append(Evidence(doc_id=doc_id, text=content[:5000], date=doc_date or "", score=float(overlap)))
    results.sort(key=lambda e: (e.score, e.date), reverse=True)
    return results[:top_k]
