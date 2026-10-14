"""Temporary raw-document ingestion adapter; replace with P1/P2 later."""
import argparse
import sqlite3
import sys
from pathlib import Path

def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    _, sep, rest = text.partition("---\n")
    if not sep:
        return {}, text
    header, sep, body = rest.partition("\n---")
    if not sep:
        return {}, text
    meta = {}
    for line in header.splitlines():
        if line.startswith((" ", "-")) or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, body.lstrip("\n")

def ingest_corpus(corpus: Path, state: Path) -> int:
    if not corpus.is_dir():
        raise FileNotFoundError(corpus)
    state.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(state / "chronicle_adapter.sqlite3") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS documents (doc_id TEXT PRIMARY KEY, doc_date TEXT, subject TEXT, body TEXT NOT NULL)")
        count = 0
        for path in sorted(corpus.rglob("*.md")):
            meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
            doc_id = meta.get("doc_id")
            if not doc_id:
                continue
            conn.execute("INSERT INTO documents (doc_id, doc_date, subject, body) VALUES (?, ?, ?, ?) ON CONFLICT(doc_id) DO UPDATE SET doc_date=excluded.doc_date, subject=excluded.subject, body=excluded.body", (doc_id, meta.get("date", ""), meta.get("subject", ""), body))
            count += 1
    print(f"[chronicle] ingested {count} documents from {corpus}", file=sys.stderr)
    return count

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    args = p.parse_args()
    ingest_corpus(args.corpus, args.state)

if __name__ == "__main__":
    main()
