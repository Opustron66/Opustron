import sqlite3
from datetime import UTC, date, datetime, timedelta

from chronicle.memory.api import MemoryAPI
from chronicle.memory.database import MemoryDatabase
from chronicle.schema import Event, Source

from .conftest import handover, make_claim


def test_memory_api_stores_events():
    api = MemoryAPI()
    event = Event("hello", Source("test://1", "test"))
    assert api.remember(event) is event
    assert api.list_memories() == [event]


def test_migrations_create_schema_once(tmp_path):
    path = tmp_path / "m.sqlite3"
    db = MemoryDatabase(path)
    assert db.schema_version == 1
    db.close()
    db = MemoryDatabase(path)  # reopening does not re-run 0001
    assert db.schema_version == 1
    tables = {r[0] for r in sqlite3.connect(path).execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"facts", "fact_sources", "entities", "entity_aliases"} <= tables


def test_handover_merges_closing_claim_and_supersedes(memory, payments):
    report = memory.ingest_claims(payments)
    assert (report.added, report.merged, report.duplicates, report.superseded) == (2, 1, 0, 1)
    alice, dana = memory.facts(predicate="owns")
    assert (alice.subject, alice.valid_from, alice.valid_to) == ("Alice Chen", date(2026, 4, 16), date(2026, 5, 12))
    assert alice.superseded_by == dana.fact_id and alice.end_reason == "superseded"
    assert [s.role for s in alice.sources] == ["opened", "closed"]
    assert alice.doc_id == "E:alice" and alice.quote == "Alice Chen owns the payments service."
    assert dana.is_open


def test_reingesting_is_a_no_op(memory, payments):
    memory.ingest_claims(payments)
    before = memory.database.query("SELECT count(*) FROM facts")[0][0]
    report = memory.ingest_claims(payments)
    assert report.duplicates == 3 and report.added == report.merged == 0
    assert memory.database.query("SELECT count(*) FROM facts")[0][0] == before


def test_closing_claim_before_opening_claim(memory, payments):
    opening, dana, closing = payments
    memory.ingest_claims([closing, dana, opening])
    alice = memory.facts(subject="Alice Chen")
    assert len(alice) == 1
    assert (alice[0].valid_from, alice[0].valid_to) == (date(2026, 4, 16), date(2026, 5, 12))
    assert alice[0].primary_source.role == "opened"


def test_out_of_order_ingestion_gives_same_answers(payments):
    forward, backward = MemoryAPI(), MemoryAPI()
    forward.ingest_claims(payments)
    backward.ingest_claims(list(reversed(payments)))
    for day in ("2026-04-20", "2026-05-11", "2026-05-12", "2026-06-01"):
        assert [f.subject for f in forward.as_of(day)] == [f.subject for f in backward.as_of(day)]


def test_restatement_adds_source_not_fact(memory, claim):
    memory.ingest_claims([
        claim("Alice Chen", "owns", "payments service", observed="2026-04-16", doc="E:1"),
        claim("alice chen", "Owns", "Payments  Service", observed="2026-04-30", doc="E:2"),
    ])
    (fact,) = memory.facts()
    assert fact.valid_from == date(2026, 4, 16)
    assert [s.doc_id for s in fact.sources] == ["E:1", "E:2"]
    assert [s.role for s in fact.sources] == ["opened", "restated"]


def test_earlier_mention_ingested_later_extends_start(memory, claim):
    memory.ingest_claims([claim("Alice Chen", "owns", "payments", observed="2026-04-30", doc="E:late")])
    memory.ingest_claims([claim("Alice Chen", "owns", "payments", observed="2026-04-16", doc="E:early")])
    (fact,) = memory.facts()
    assert fact.valid_from == date(2026, 4, 16)


def test_owner_returning_later_is_a_new_fact(memory, payments, claim):
    memory.ingest_claims(payments)
    memory.ingest_claims([claim("Alice Chen", "owns", "payments service", observed="2026-06-01", doc="E:back")])
    owners = [(f.subject, f.valid_from, f.valid_to) for f in memory.facts(predicate="owns")]
    assert owners == [
        ("Alice Chen", date(2026, 4, 16), date(2026, 5, 12)),
        ("Dana Lee", date(2026, 5, 12), date(2026, 6, 1)),
        ("Alice Chen", date(2026, 6, 1), None),
    ]


def test_multi_valued_predicates_coexist(memory, claim):
    memory.ingest_claims([
        claim("Alice Chen", "works_on", "Atlas", observed="2026-04-16"),
        claim("Alice Chen", "works_on", "payments", observed="2026-04-20"),
    ])
    assert len(memory.as_of("2026-05-01", subject="Alice Chen")) == 2


def test_status_supersedes_per_subject(memory, claim):
    memory.ingest_claims([
        claim("migration", "status", "blocked", observed="2026-04-16"),
        claim("migration", "status", "done", observed="2026-04-25"),
    ])
    assert memory.value_at("migration", "status", "2026-04-20").object == "blocked"
    assert memory.value_at("migration", "status", "2026-04-25").object == "done"


def test_moved_deadline_replaces_the_old_one_from_when_it_was_said(memory, claim):
    memory.ingest_claims([
        claim("migration", "deadline", "due", observed="2026-04-16", valid_from=date(2026, 4, 24)),
        claim("migration", "deadline", "due", observed="2026-04-20", valid_from=date(2026, 5, 1)),
    ])
    assert memory.value_at("migration", "deadline", "2026-04-18").event_at == date(2026, 4, 24)
    moved = memory.value_at("migration", "deadline", "2026-04-21")
    assert moved.event_at == date(2026, 5, 1)
    assert moved.to_claim().valid_from == date(2026, 5, 1)
    assert "2026-05-01" in moved.content


def test_supersession_writes_a_new_version(memory, payments):
    memory.ingest_claims(payments)
    alice = memory.facts(subject="Alice Chen")[0]
    versions = memory.versions(alice.fact_id)
    assert versions[0].valid_to is None and versions[0].replaced_at is not None
    assert versions[-1].valid_to == date(2026, 5, 12) and versions[-1].replaced_at is None


def test_known_at_shows_what_we_believed_before_a_later_email(payments):
    now = [datetime(2026, 4, 16, 12, tzinfo=UTC)]
    memory = MemoryAPI(MemoryDatabase(clock=lambda: now[0]))
    memory.ingest_claims(payments[:1])
    learned_alice = now[0]
    now[0] += timedelta(days=30)
    memory.ingest_claims(payments[1:])

    # On 1 June, as we know it now: Dana. As we knew it on 16 April: Alice, still open.
    assert [f.subject for f in memory.as_of("2026-06-01")] == ["Dana Lee"]
    believed = memory.as_of("2026-06-01", known_at=learned_alice)
    assert [(f.subject, f.valid_to) for f in believed] == [("Alice Chen", None)]
    assert memory.as_of("2026-06-01", known_at=datetime(2026, 4, 1, tzinfo=UTC)) == []


def test_persists_across_reopen(tmp_path, payments):
    path = tmp_path / "memory.sqlite3"
    with MemoryAPI(path) as memory:
        memory.ingest_claims(payments)
    with MemoryAPI(path) as reopened:
        assert reopened.holder_at("owns", "payments service", "2026-05-03").subject == "Alice Chen"
        assert reopened.ingest_claims(payments).duplicates == 3


def test_contradictory_dates_keep_the_end(memory, claim):
    memory.ingest_claims([claim("Bob", "owns", "search", observed="2026-05-01",
                                valid_from=date(2026, 5, 10), valid_to=date(2026, 5, 2))])
    (fact,) = memory.facts()
    assert fact.valid_from is None and fact.valid_to == date(2026, 5, 2)


def test_entities_are_created_for_subjects_and_object_entities(memory, payments, claim):
    memory.ingest_claims([*payments, claim("migration", "status", "blocked", observed="2026-04-16")])
    names = {e.name: e for e in memory.entities()}
    assert {"Alice Chen", "Dana Lee", "payments service", "migration"} <= names.keys()
    assert "blocked" not in names
    assert names["Alice Chen"].entity_type == "person"
    assert names["payments service"].first_seen == date(2026, 4, 16)


def test_notes_supersede_and_retire():
    db = MemoryDatabase()
    t = datetime(2026, 5, 1, 9, tzinfo=UTC)
    tea = db.add_note("User prefers tea", source="hermes://test", at=t)
    coffee = db.add_note("User prefers coffee", source="hermes://test", at=t + timedelta(days=1),
                         supersedes="user prefers TEA")
    assert db.retire_note("User prefers coffee", at=t + timedelta(days=2)) == 1
    by_id = {f.fact_id: f for f in db.facts()}
    assert by_id[tea].superseded_by == coffee and by_id[tea].valid_to == t + timedelta(days=1)
    assert by_id[coffee].end_reason == "retired"
    assert db.retire_note("User prefers coffee", at=t + timedelta(days=3)) == 0


def test_handover_helper_matches_p1_prompt():
    new, old = handover("Dana", "Alice", "payments", "2026-05-12")
    assert new.valid_from == date(2026, 5, 12) and new.valid_to is None
    assert old.valid_from is None and old.valid_to == date(2026, 5, 12)
    assert make_claim("x", "owns", "y", observed="2026-01-01").valid_from == date(2026, 1, 1)
