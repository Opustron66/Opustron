from fastapi.testclient import TestClient

from chronicle.memory.__main__ import main as memory_main
from chronicle.memory.server import create_app

from .test_api import PART_A, PART_B, write_claims


def client_for(tmp_path, claims=PART_A + PART_B):
    state = tmp_path / "state"
    write_claims(state, claims)
    return TestClient(create_app(state)), state


def test_facts_as_of(tmp_path):
    client, _ = client_for(tmp_path)
    may3 = client.get("/api/facts", params={"as_of": "2026-05-03", "predicate": "owns"}).json()
    assert [f["subject"] for f in may3] == ["Alice Chen"]
    assert may3[0]["valid_to"] == "2026-05-12" and may3[0]["doc_id"].startswith("E:")
    may12 = client.get("/api/facts?as_of=2026-05-12&predicate=owns").json()
    assert [f["subject"] for f in may12] == ["Dana Lee"]
    assert len(client.get("/api/facts").json()) == 3


def test_entities_and_history(tmp_path):
    client, _ = client_for(tmp_path)
    entities = {e["name"]: e for e in client.get("/api/entities").json()}
    service = entities["payments service"]
    history = client.get(f"/api/entities/{service['entity_id']}/history").json()
    assert history["entity"]["name"] == "payments service"
    assert [f["subject"] for f in history["facts"]] == ["Alice Chen", "Dana Lee"]
    assert client.get("/api/entities/nope/history").status_code == 404


def test_timeline_search_span_versions(tmp_path):
    client, _ = client_for(tmp_path)
    timeline = client.get("/api/timeline", params={"start": "2026-05-01", "end": "2026-05-31"}).json()
    assert [(e["at"], e["change"], e["fact"]["subject"]) for e in timeline] == [
        ("2026-05-12", "ended", "Alice Chen"), ("2026-05-12", "started", "Dana Lee"),
    ]
    hits = client.get("/api/search", params={"q": "payments owner", "as_of": "2026-05-03"}).json()
    assert hits[0]["fact"]["subject"] == "Alice Chen"
    assert client.get("/api/span").json() == {"start": "2026-04-16", "end": "2026-05-12"}
    alice_id = timeline[0]["fact"]["fact_id"]
    assert len(client.get(f"/api/facts/{alice_id}/versions").json()) == 2
    assert client.get("/api/facts/nope/versions").status_code == 404


def test_bad_dates_are_400(tmp_path):
    client, _ = client_for(tmp_path)
    assert client.get("/api/facts?as_of=May%203").status_code == 400
    assert client.get("/api/timeline?start=x&end=2026-05-01").status_code == 400


def test_picks_up_claims_appended_while_running(tmp_path):
    client, state = client_for(tmp_path, PART_A)
    assert [f["subject"] for f in client.get("/api/facts?as_of=2026-05-20&predicate=owns").json()] == ["Alice Chen"]
    write_claims(state, PART_B, mode="a")
    assert [f["subject"] for f in client.get("/api/facts?as_of=2026-05-20&predicate=owns").json()] == ["Dana Lee"]


def test_sync_cli(tmp_path):
    state = tmp_path / "state"
    write_claims(state, PART_A)
    assert memory_main(["sync", "--state", str(state)]) == 0
    assert (state / "memory.sqlite3").is_file()
