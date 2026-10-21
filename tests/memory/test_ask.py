from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from chronicle.memory import MemoryAPI
from chronicle.memory.server import create_app
from chronicle.schema import Claim


@pytest.fixture
def memory():
    with MemoryAPI() as memory:
        memory.ingest_claims([
            Claim(subject="Maya Patel", predicate="owns", object="billing service",
                  valid_from="2026-06-01", observed_at="2026-06-01",
                  doc_id="DEMO:original", quote="Maya Patel owns the billing service."),
            Claim(subject="Noah Williams", predicate="owns", object="billing service",
                  valid_from="2026-06-10", observed_at="2026-06-10",
                  doc_id="DEMO:handover", quote="Noah Williams takes over billing from Maya Patel."),
        ])
        yield memory


@pytest.mark.parametrize(("question", "day", "owner", "source"), [
    ("Who owned billing on June 9?", "2026-06-20", "Maya Patel", "DEMO:original"),
    ("Who owns billing?", "2026-06-09", "Maya Patel", "DEMO:original"),
    ("Who owns billing?", "2026-06-10", "Noah Williams", "DEMO:handover"),
])
def test_ask_filters_evidence_and_returns_real_citations(memory, question, day, owner, source):
    def complete(messages, schema):
        prompt = messages[1]["content"]
        assert f'): {owner} owns' in prompt
        other = "Noah Williams" if owner == "Maya Patel" else "Maya Patel"
        assert f'): {other} owns' not in prompt
        assert "Answer as of 2026-06-" in prompt
        return {"answer": owner, "source_ids": [source, "invented", source]}

    with patch("chronicle.reason.answerer.llm.complete", side_effect=complete) as model:
        response = TestClient(create_app(memory)).post("/api/ask", json={"question": question, "as_of": day})
    assert response.status_code == 200
    assert response.json() == {"answer": owner, "source_ids": [source], "citations": [{"doc_id": source}]}
    model.assert_called_once()


def test_unknown_question_abstains_without_model(memory):
    with patch("chronicle.reason.answerer.llm.complete") as model:
        response = TestClient(create_app(memory)).post("/api/ask", json={"question": "cafeteria menu"})
    assert response.json() == {"answer": "Not in the corpus", "source_ids": [], "citations": []}
    model.assert_not_called()


@pytest.mark.parametrize("body", [
    {}, {"question": " "}, {"question": "billing", "as_of": "June 20"},
    {"question": "billing", "as_of": "2026-06-31"},
])
def test_invalid_requests_are_rejected(memory, body):
    assert TestClient(create_app(memory)).post("/api/ask", json=body).status_code == 422


def test_invalid_question_date_is_400(memory):
    response = TestClient(create_app(memory)).post("/api/ask", json={"question": "billing on June 31"})
    assert response.status_code == 400


def test_provider_error_is_safe_and_not_a_fake_answer(memory):
    with patch("chronicle.reason.answerer.llm.complete", side_effect=RuntimeError("SECRET KEY and private corpus")):
        response = TestClient(create_app(memory)).post("/api/ask", json={"question": "billing"})
    assert response.status_code == 502
    assert "SECRET" not in response.text
    assert "answer" not in response.json()


def test_ask_refreshes_claims_appended_to_served_state(tmp_path):
    claims = tmp_path / "claims.jsonl"
    claims.write_text("", encoding="utf-8")
    client = TestClient(create_app(tmp_path))
    assert client.post("/api/ask", json={"question": "billing"}).json()["source_ids"] == []
    claim = Claim(subject="Maya Patel", predicate="owns", object="billing", doc_id="new", quote="Maya owns billing.")
    claims.write_text(claim.model_dump_json() + "\n", encoding="utf-8")
    with patch("chronicle.reason.answerer.llm.complete", return_value={"answer": "Maya Patel", "source_ids": ["new"]}):
        response = client.post("/api/ask", json={"question": "billing"})
    assert response.json()["citations"] == [{"doc_id": "new"}]
