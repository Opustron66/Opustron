from datetime import date

from chronicle.memory.api import CLAIMS_FILE, DB_FILE, MemoryAPI

from .conftest import handover, make_claim

PART_A = [
    make_claim("Alice Chen", "owns", "payments service", observed="2026-04-16",
               doc="E:2026-04-16T09-12-00__aaaa0001", quote="Alice Chen owns the payments service."),
    make_claim("migration", "deadline", "due", observed="2026-04-16", valid_from=date(2026, 4, 24),
               doc="E:2026-04-16T09-12-00__aaaa0001", quote="The migration is due next Friday."),
]
PART_B = handover("Dana Lee", "Alice Chen", "payments service", "2026-05-12", doc="E:2026-05-12T10-00-00__bbbb0002")


def write_claims(state, claims, mode="w"):
    state.mkdir(parents=True, exist_ok=True)
    with (state / CLAIMS_FILE).open(mode, encoding="utf-8") as out:
        for c in claims:
            out.write(c.model_dump_json() + "\n")


def test_from_state_loads_p1_claims_and_syncs_appends(tmp_path):
    state = tmp_path / "state"
    write_claims(state, PART_A)
    with MemoryAPI.from_state(state) as memory:
        assert memory.holder_at("owns", "payments service", "2026-05-20").subject == "Alice Chen"
    assert (state / DB_FILE).is_file()

    write_claims(state, PART_B, mode="a")  # P1 ingests part B in a separate process
    with MemoryAPI.from_state(state) as memory:
        assert memory.holder_at("owns", "payments service", "2026-05-20").subject == "Dana Lee"
        assert memory.holder_at("owns", "payments service", "2026-05-03").subject == "Alice Chen"
        assert len(memory.facts()) == 3


def test_from_state_without_claims_is_empty(tmp_path):
    with MemoryAPI.from_state(tmp_path) as memory:
        assert memory.facts() == []
        assert memory.sync_claims_file(tmp_path / "missing.jsonl").added == 0


def test_to_claim_round_trips_provenance(memory):
    memory.ingest_claims(PART_A + PART_B)
    alice = memory.facts(subject="Alice Chen")[0].to_claim()
    assert alice.doc_id == "E:2026-04-16T09-12-00__aaaa0001"
    assert alice.quote == "Alice Chen owns the payments service."
    assert (alice.valid_from, alice.valid_to, alice.observed_at) == (date(2026, 4, 16), date(2026, 5, 12), date(2026, 4, 16))
    deadline = memory.facts(predicate="deadline")[0].to_claim()
    assert deadline.valid_from == date(2026, 4, 24) and deadline.object == "due"


def test_fact_lookup_and_current(memory):
    memory.ingest_claims(PART_A + PART_B)
    dana = memory.holder_at("owns", "payments service", "2026-06-01")
    assert memory.fact(dana.fact_id).subject == "Dana Lee"
    assert memory.fact("nope") is None
    assert "Dana Lee" in {f.subject for f in memory.current(predicate="owns")}
