import json
from datetime import date
from pathlib import Path

from chronicle.ingest.pipeline import ingest_corpus, read_claims, run_ingest
from chronicle.schema import Document

FIX = Path(__file__).parent.parent / "fixtures" / "corpus"


class FakeLLM:
    """Returns claims quoting the first sentence of whatever document it is given."""

    def __init__(self):
        self.calls = 0

    def complete(self, messages, schema=None):
        self.calls += 1
        text = messages[1]["content"]
        quote = text.split(".")[0] + "."
        return json.dumps({"claims": [{"subject": "alice chen", "predicate": "owns", "object": "payments",
                                       "valid_from": "today", "quote": quote}]})


def test_end_to_end_idempotent(tmp_path):
    llm = FakeLLM()
    s1 = ingest_corpus(FIX, tmp_path, llm)
    assert s1.documents == 3 and s1.claims == 3 and llm.calls == 3
    claims = read_claims(tmp_path / "claims.jsonl")
    assert {c.doc_id for c in claims} >= {"E:2026-04-16T09-12-00__aaaa0001"}
    assert all(c.observed_at is not None and c.quote for c in claims)
    assert {c.valid_from for c in claims} == {c.observed_at for c in claims}  # "today" == doc date

    s2 = ingest_corpus(FIX, tmp_path, llm)  # re-run: nothing new, no LLM calls
    assert s2.documents == 0 and s2.skipped == 3 and llm.calls == 3
    assert len(read_claims(tmp_path / "claims.jsonl")) == 3


def test_forced_rerun_hits_cache(tmp_path):
    llm = FakeLLM()
    ingest_corpus(FIX, tmp_path / "a", llm, cache_dir=tmp_path / "cache")
    calls = llm.calls
    s = ingest_corpus(FIX, tmp_path / "b", llm, cache_dir=tmp_path / "cache")
    assert llm.calls == calls and s.cache_hits == 3


def test_failure_does_not_abort_or_mark_done(tmp_path):
    class Flaky(FakeLLM):
        def complete(self, messages, schema=None):
            if "Dana" in messages[1]["content"]:
                raise RuntimeError("boom")
            return super().complete(messages, schema)

    s = ingest_corpus(FIX, tmp_path, Flaky())
    assert s.failed == 1 and s.documents == 2
    assert "E:2026-05-12T10-00-00__bbbb0002" not in json.loads((tmp_path / "ingested_docs.json").read_text())


def test_undated_doc_counts_as_failed(tmp_path):
    doc = Document(doc_id="X", text="Hello there.", doc_date=None)
    s = run_ingest([doc], tmp_path, FakeLLM())
    assert s.failed == 1 and s.claims == 0


def test_canonical_names_stable_across_parts(tmp_path):
    ingest_corpus(FIX / "part_a", tmp_path, FakeLLM())
    ingest_corpus(FIX / "part_b", tmp_path, FakeLLM())
    assert {c.subject for c in read_claims(tmp_path / "claims.jsonl")} == {"alice chen"}


def test_cli_missing_corpus(tmp_path, capsys):
    from chronicle.ingest.__main__ import main

    assert main(["--corpus", str(tmp_path / "nope"), "--state", str(tmp_path)]) == 2
