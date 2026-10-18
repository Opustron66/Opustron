import json
from datetime import date

import pytest

from chronicle.claim_normalization import normalize_claim_value
from chronicle.ingest.extractor import ClaimExtractor
from chronicle.memory import MemoryAPI
from chronicle.schema import Claim, Document


def extract(rows, text, day="2026-06-12"):
    class FakeLLM:
        def complete(self, messages, schema=None):
            return json.dumps({"claims": rows})
    extractor = ClaimExtractor(FakeLLM())
    return extractor, extractor.extract(Document(doc_id="revision", text=text, doc_date=day))


@pytest.mark.parametrize("predicate", ["status", "work_email", "contact_email", "email_address", "email"])
def test_email_values_use_contact_predicate(predicate):
    assert normalize_claim_value(predicate, "maya@example.test") == ("email", "maya@example.test")
    assert normalize_claim_value("status", "active") == ("status", "active")


def test_same_document_deadline_replacement_drops_spurious_close_and_supersedes():
    quote = "The invoice export deadline moved from 2026-06-18 to 2026-06-25."
    ex, claims = extract([
        {"subject": "invoice export", "predicate": "deadline", "object": "deadline", "valid_from": "2026-06-25", "quote": quote},
        {"subject": "invoice export", "predicate": "deadline", "object": "deadline", "valid_to": "2026-06-18", "quote": quote},
    ], quote)
    assert ex.dropped == 1 and len(claims) == 1
    assert claims[0].object == "due" and claims[0].valid_from == date(2026, 6, 25)
    old = Claim(subject="invoice export", predicate="deadline", object="due date", valid_from="2026-06-18",
                observed_at="2026-06-03", doc_id="original", quote="Export due June 18.")
    for records in [[old, *claims], [*claims, old]]:
        with MemoryAPI() as memory:
            memory.ingest_claims(records)
            assert len(memory.facts()) == 2
            assert memory.value_at("invoice export", "deadline", "2026-06-05").event_at == date(2026, 6, 18)
            assert memory.value_at("invoice export", "deadline", "2026-06-12").event_at == date(2026, 6, 25)
            assert memory.as_of("2026-05-31") == []


def test_ownership_closure_and_standalone_dated_closure_are_preserved():
    quote = "Noah takes billing from Maya; the demo ended today."
    _, claims = extract([
        {"subject":"Noah", "predicate":"owns", "object":"billing", "valid_from":"today", "quote":quote},
        {"subject":"Maya", "predicate":"owns", "object":"billing", "valid_to":"today", "quote":quote},
        {"subject":"demo", "predicate":"scheduled_for", "object":"scheduled", "valid_to":"today", "quote":quote},
    ], quote)
    assert len(claims) == 3
    assert claims[1].valid_from is None and claims[1].valid_to == date(2026, 6, 12)
    assert claims[2].valid_from is None


def test_email_does_not_compete_with_status_or_create_email_entity():
    with MemoryAPI() as memory:
        memory.ingest_claims([
            Claim(subject="Maya", predicate="status", object="active", valid_from="2026-06-01", doc_id="a", quote="Maya is active."),
            Claim(subject="Maya", predicate="status", object="maya@example.test", valid_from="2026-06-02", doc_id="b", quote="Maya email maya@example.test."),
            Claim(subject="Maya", predicate="email", object="maya@work.test", valid_from="2026-06-03", doc_id="c", quote="Maya also uses maya@work.test."),
        ])
        facts = memory.as_of("2026-06-20")
        assert len(facts) == 3  # multiple contact addresses may coexist
        assert len([f for f in facts if f.predicate == "email"]) == 2
        assert [f.object for f in facts if f.predicate == "status"] == ["active"]
        assert not any("@" in e.name for e in memory.entities())


def test_normalization_keeps_descriptive_event_values_and_source_quotes():
    assert normalize_claim_value("scheduled_for", "design review with finance") == ("scheduled_for", "design review with finance")
    quote = "Maya's work email is maya@example.test."
    _, claims = extract([{"subject":"Maya", "predicate":"status", "object":"maya@example.test", "quote":quote}], quote)
    assert claims[0].predicate == "email" and claims[0].quote == quote


def test_unresolved_replacement_does_not_discard_stated_closure():
    quote = "The export deadline is changing."
    ex, claims = extract([
        {"subject":"export", "predicate":"deadline", "object":"due", "valid_from":"when stars align", "quote":quote},
        {"subject":"export", "predicate":"deadline", "object":"due", "valid_to":"today", "quote":quote},
    ], quote)
    assert len(claims) == 2 and ex.dropped == 0
