from datetime import date
from pathlib import Path

from chronicle.ingest.parsers.markdown import parse_document, split_frontmatter, to_date

FIX = Path(__file__).parent.parent / "fixtures" / "corpus"


def test_split_frontmatter_roundtrip():
    meta, body = split_frontmatter("---\ndoc_id: X\ndate: 2026-04-16\n---\n\nHello")
    assert meta["doc_id"] == "X" and body == "Hello"


def test_split_frontmatter_missing_or_broken():
    assert split_frontmatter("no header") == ({}, "no header")
    assert split_frontmatter("---\n: : bad\n[\n---\nx")[0] == {}
    assert split_frontmatter("---\nnever closed")[0] == {}


def test_to_date_variants():
    assert to_date("2026-04-16T09:12:00Z") == date(2026, 4, 16)
    assert to_date(date(2026, 1, 2)) == date(2026, 1, 2)
    assert to_date("garbage") is None and to_date(None) is None


def test_parse_document_email():
    doc = parse_document(FIX / "part_a/email/e1.md", root=FIX / "part_a", part="a")
    assert doc.doc_id == "E:2026-04-16T09-12-00__aaaa0001"
    assert doc.doc_date == date(2026, 4, 16) and doc.kind == "email" and doc.part == "a"
    assert doc.text.startswith("Alice Chen owns")


def test_parse_document_without_date_falls_back_to_mtime(tmp_path):
    p = tmp_path / "note.md"
    p.write_text("just a note")
    doc = parse_document(p, root=tmp_path)
    assert doc.doc_id == "M:note.md" and doc.metadata["date_source"] == "mtime"
