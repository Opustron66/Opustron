import json
from datetime import date

import pytest

from chronicle.ingest.cache import DiskCache
from chronicle.ingest.extractor import ClaimExtractor, parse_llm_json
from chronicle.schema import Document, Event

DOC = Document(doc_id="E:1", text="Alice Chen owns the payments service. The migration is due next Friday.",
               doc_date=date(2026, 5, 12), kind="email")


class FakeLLM:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), 0

    def complete(self, messages, schema=None):
        self.calls += 1
        return self.replies.pop(0)


GOOD = json.dumps({"claims": [
    {"subject": "Alice Chen", "predicate": "owns", "object": "payments service",
     "valid_from": None, "valid_to": None, "quote": "Alice Chen owns the payments service.", "confidence": 0.9},
    {"subject": "migration", "predicate": "deadline", "object": "due", "valid_from": "next Friday",
     "quote": "The migration is due next Friday."},
    {"subject": "Bob", "predicate": "owns", "object": "billing", "quote": "Bob owns billing."},  # hallucinated
]})


def test_extract_stamps_with_document_date_and_drops_hallucinations():
    ex = ClaimExtractor(FakeLLM([GOOD]))
    claims = ex.extract(DOC)
    assert len(claims) == 2 and ex.dropped == 1
    assert all(c.observed_at == date(2026, 5, 12) and c.doc_id == "E:1" for c in claims)
    assert claims[0].valid_from == date(2026, 5, 12)
    assert claims[1].valid_from == date(2026, 5, 22)  # "next Friday" = Friday of next week, vs doc date not today


def test_cache_makes_rerun_free(tmp_path):
    llm = FakeLLM([GOOD])
    ex = ClaimExtractor(llm, cache=DiskCache(tmp_path))
    first = ex.extract(DOC)
    second = ex.extract(DOC)
    assert llm.calls == 1 and first == second and ex.cache.hits == 1


def test_repair_retry_then_success_and_final_failure():
    assert len(ClaimExtractor(FakeLLM(["oops", GOOD])).extract(DOC)) == 2
    with pytest.raises(ValueError):
        ClaimExtractor(FakeLLM(["oops", "still bad"])).extract(DOC)


def test_undated_document_is_refused():
    with pytest.raises(ValueError, match="no date"):
        ClaimExtractor(FakeLLM([GOOD])).extract(DOC.model_copy(update={"doc_date": None}))


def test_unresolvable_date_lowers_confidence():
    reply = json.dumps({"claims": [{"subject": "A", "predicate": "deadline", "object": "x",
                                    "valid_from": "when stars align", "quote": "Alice Chen owns"}]})
    (c,) = ClaimExtractor(FakeLLM([reply])).extract(DOC)
    assert c.confidence <= 0.4


@pytest.mark.parametrize("raw", [
    '```json\n{"claims": []}\n```', '<think>hmm</think>{"claims": []}', 'Sure! {"claims": []}', "[]",
])
def test_parse_llm_json_tolerant(raw):
    assert parse_llm_json(raw) == []


@pytest.mark.parametrize("raw", ["", "no json", '{"foo": 1}'])
def test_parse_llm_json_rejects(raw):
    with pytest.raises(ValueError):
        parse_llm_json(raw)


def test_legacy_extract_entities():
    from chronicle.ingest.extractor import extract_entities
    from chronicle.schema import Source

    ents = extract_entities(Event(content="Met Alice, Bob.", source=Source(uri="u", kind="k")))
    assert [e.name for e in ents] == ["Alice", "Bob"]


def test_parse_llm_json_ignores_braces_in_reasoning_text():
    raw = ('Here\'s a thinking process:\n1. Output {"ok": true} maybe?\n2. Use {"claims": [1]} no.\n'
           'Final:\n{"claims": [{"subject": "a", "predicate": "owns", "object": "b", "quote": "q"}]}')
    (c,) = parse_llm_json(raw)
    assert c["subject"] == "a"


def test_closing_claim_keeps_start_unknown():
    reply = json.dumps({"claims": [
        {"subject": "Alice Chen", "predicate": "owns", "object": "payments service", "valid_to": "today",
         "quote": "Alice Chen owns the payments service."}]})
    (c,) = ClaimExtractor(FakeLLM([reply])).extract(DOC)
    assert c.valid_from is None and c.valid_to == date(2026, 5, 12)
