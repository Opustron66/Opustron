import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from adapters.chronicle.answer import run
from chronicle.memory import MemoryAPI
from chronicle.memory.server import create_app
from chronicle.reason.planner import plan_query
from chronicle.reason.retriever import retrieve
from chronicle.schema import Claim


def write_claims(state, claims, mode="w"):
    with (state / "claims.jsonl").open(mode, encoding="utf-8") as stream:
        for claim in claims:
            stream.write(claim.model_dump_json() + "\n")


@pytest.fixture
def claims():
    return [
        Claim(subject="Maya Patel", predicate="owns", object="billing service",
              valid_from="2026-06-01", observed_at="2026-06-01", doc_id="original",
              quote="Maya Patel owns the billing service."),
        Claim(subject="Noah Williams", predicate="owns", object="billing service",
              valid_from="2026-06-10", observed_at="2026-06-10", doc_id="handover",
              quote="Noah Williams takes over billing from Maya Patel."),
    ]


@pytest.mark.parametrize(("question", "as_of", "owner", "source"), [
    ("Who owned billing on 2026-06-09?", None, "Maya Patel", "original"),
    ("Who owns billing?", "2026-06-09", "Maya Patel", "original"),
    ("Who owns billing?", "2026-06-10", "Noah Williams", "handover"),
    ("Who owned billing on June 9?", "2026-06-20", "Maya Patel", "original"),
])
def test_jsonl_and_ui_send_identical_temporal_evidence(tmp_path, claims, question, as_of, owner, source):
    write_claims(tmp_path, claims)
    payload = {"question": question, "as_of": as_of}
    prompts = []

    def complete(messages, schema):
        prompts.append(messages)
        assert f'"subject": "{owner}"' in messages[1]["content"]
        other = "Noah Williams" if owner == "Maya Patel" else "Maya Patel"
        assert f'"subject": "{other}"' not in messages[1]["content"]
        return {"answer": owner, "source_ids": [source, "invented"]}

    with patch("chronicle.reason.answerer.llm.complete", side_effect=complete):
        output = io.StringIO()
        run(tmp_path, io.StringIO(json.dumps({"id": "q1", **payload}) + "\n"), output)
        response = TestClient(create_app(tmp_path)).post("/api/ask", json=payload)
    assert response.status_code == 200
    cli = json.loads(output.getvalue())
    assert cli["answer"] == response.json()["answer"] == owner
    assert cli["source_ids"] == response.json()["source_ids"] == [source]
    assert prompts[0] == prompts[1]
    assert (tmp_path / "memory.sqlite3").is_file()


def test_adapter_state_resyncs_new_claims_and_survives_reopen(tmp_path, claims):
    write_claims(tmp_path, claims[:1])
    plan = plan_query("billing on 2026-06-20")
    assert [e.doc_id for e in retrieve(plan, tmp_path)] == ["original"]
    write_claims(tmp_path, claims[1:], mode="a")
    assert [e.doc_id for e in retrieve(plan, tmp_path)] == ["handover"]
    with MemoryAPI.from_state(tmp_path) as memory:
        assert len(memory.facts()) == 2  # repeated sync did not duplicate claims
    (tmp_path / "claims.jsonl").unlink()
    assert [e.doc_id for e in retrieve(plan, tmp_path)] == ["handover"]


def test_history_retrieval_keeps_both_owners(tmp_path, claims):
    write_claims(tmp_path, claims)
    evidence = retrieve(plan_query("Who owned billing before Noah?"), tmp_path)
    assert {e.doc_id for e in evidence} == {"original", "handover"}


def test_unknown_question_abstains_in_both_entry_points(tmp_path, claims):
    write_claims(tmp_path, claims)
    with patch("chronicle.reason.answerer.llm.complete") as complete:
        output = io.StringIO()
        run(tmp_path, io.StringIO('{"id":"q1","question":"cafeteria menu"}\n'), output)
        response = TestClient(create_app(tmp_path)).post("/api/ask", json={"question": "cafeteria menu"})
    assert json.loads(output.getvalue())["answer"] == response.json()["answer"] == "Not in the corpus"
    assert json.loads(output.getvalue())["source_ids"] == response.json()["source_ids"] == []
    complete.assert_not_called()


@pytest.mark.parametrize("invalid", ["2026-06-31", "private-invalid-date", 20, []])
def test_adapter_skips_invalid_as_of_then_continues(tmp_path, claims, capsys, invalid):
    write_claims(tmp_path, claims)
    records = [
        {"id": "bad", "question": "billing", "as_of": invalid},
        {"id": "good", "question": "cafeteria menu"},
    ]
    output = io.StringIO()
    run(tmp_path, io.StringIO("\n".join(json.dumps(r) for r in records)), output)
    assert json.loads(output.getvalue())["id"] == "good"
    error = capsys.readouterr().err
    assert "line 1: invalid 'as_of' date" in error
    assert "private" not in error
