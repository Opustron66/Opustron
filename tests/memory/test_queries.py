from datetime import date

from .conftest import make_claim


def test_as_of_on_and_around_handover_day(memory, payments):
    memory.ingest_claims(payments)
    owner = lambda day: memory.holder_at("owns", "payments service", day)
    assert owner("2026-04-15") is None
    assert owner("2026-05-03").subject == "Alice Chen"
    assert owner("2026-05-11").subject == "Alice Chen"
    assert owner("2026-05-12").subject == "Dana Lee"  # half-open: the new owner holds on the day
    assert owner(date(2026, 7, 1)).subject == "Dana Lee"


def test_as_of_filters(memory, payments, claim):
    memory.ingest_claims([*payments, claim("Alice Chen", "works_on", "Atlas", observed="2026-04-20")])
    assert {f.predicate for f in memory.as_of("2026-05-01", subject="alice chen")} == {"owns", "works_on"}
    assert [f.object for f in memory.as_of("2026-05-01", predicate="works on")] == ["Atlas"]


def test_history_includes_superseded_facts_and_object_side(memory, payments):
    memory.ingest_claims(payments)
    alice = memory.history("Alice Chen")
    assert [(f.subject, f.valid_to) for f in alice] == [("Alice Chen", date(2026, 5, 12))]
    service = memory.history("payments service")
    assert [f.subject for f in service] == ["Alice Chen", "Dana Lee"]
    entity_id = memory.entity("payments service").entity_id
    assert [f.fact_id for f in memory.history(entity_id)] == [f.fact_id for f in service]


def test_aliases_resolve_to_entity(memory, payments):
    memory.ingest_claims(payments)
    memory.add_alias("payments", "payments service")
    record = memory.entity("Payments")
    assert record.name == "payments service" and "payments" in record.aliases
    assert len(memory.history("payments")) == 2


def test_timeline_lists_starts_and_ends_in_order(memory, payments):
    memory.ingest_claims(payments)
    events = [(e.at, e.change, e.fact.subject) for e in memory.timeline("2026-04-01", "2026-05-31")]
    assert events == [
        (date(2026, 4, 16), "started", "Alice Chen"),
        (date(2026, 5, 12), "ended", "Alice Chen"),
        (date(2026, 5, 12), "started", "Dana Lee"),
    ]
    assert [e.change for e in memory.timeline("2026-05-01", "2026-05-11")] == []
    assert len(memory.timeline("2026-04-01", "2026-05-31", entity="Dana Lee")) == 1


def test_span_covers_all_statements(memory, payments):
    assert memory.span() == (None, None)
    memory.ingest_claims([*payments, make_claim("x", "deadline", "due", observed="2026-05-20",
                                                 valid_from=date(2026, 6, 3))])
    assert memory.span() == (date(2026, 4, 16), date(2026, 5, 20))


def test_fact_dict_has_ui_fields(memory, payments):
    memory.ingest_claims(payments)
    data = memory.holder_at("owns", "payments service", "2026-05-03").to_dict()
    assert {k: data[k] for k in ("subject", "predicate", "object", "valid_from", "valid_to", "doc_id")} == {
        "subject": "Alice Chen", "predicate": "owns", "object": "payments service",
        "valid_from": "2026-04-16", "valid_to": "2026-05-12", "doc_id": "E:alice",
    }
    assert data["quote"] and data["fact_id"] and len(data["sources"]) == 2
