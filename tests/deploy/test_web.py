"""Production paths are exercised without model calls or credentials."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.llm_client import LLMClient
from chronicle.reason.models import AnswerResult
from chronicle.schema import Claim
from chronicle.web import create_app

@pytest.fixture
def setup(tmp_path, monkeypatch):
    static = tmp_path / "ui"
    static.mkdir()
    (static / "index.html").write_text("<html>Chronicle production UI</html>")
    (static / "app.js").write_text("console.log('built asset')")
    state = tmp_path / "state"
    state.mkdir()
    claim = Claim(subject="Maya Patel", predicate="owns", object="billing service",
                  valid_from="2026-05-01", observed_at="2026-05-01", doc_id="demo-1",
                  quote="Maya Patel owns the billing service.")
    (state / "claims.jsonl").write_text(claim.model_dump_json() + "\n", encoding="utf-8")
    monkeypatch.delenv("CHRONICLE_WEB_USERNAME", raising=False)
    monkeypatch.delenv("CHRONICLE_WEB_PASSWORD", raising=False)
    monkeypatch.setenv("CHRONICLE_WEB_STATIC_DIR", str(static))
    monkeypatch.setenv("CHRONICLE_STATE_DIR", str(state))
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "0")
    monkeypatch.setenv("CHRONICLE_WEB_EPHEMERAL", "0")
    monkeypatch.delenv("CHRONICLE_STATE_SNAPSHOT_URL", raising=False)
    monkeypatch.delenv("CHRONICLE_STATE_SNAPSHOT_SHA256", raising=False)
    monkeypatch.setenv("CHRONICLE_WEB_ASKS_PER_MINUTE", "6")
    monkeypatch.setattr(LLMClient, "complete", Mock(side_effect=AssertionError("No model calls permitted")))
    monkeypatch.setattr("chronicle.web.get_logger", lambda: EgressLogger(tmp_path / "egress.log"))
    return state


def test_imported_memory_and_built_ui_share_one_origin(setup):
    with TestClient(create_app()) as client:
        assert client.get("/healthz").json() == {"status": "ok", "memory_loaded": True}
        assert "production UI" in client.get("/").text
        assert client.get("/app.js").status_code == 200
        response = client.get("/api/facts")
        assert response.json()[0]["subject"] == "Maya Patel"
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/api/egress").json() == []
        assert client.get("/api/does-not-exist").status_code == 404
    assert (setup / "memory.sqlite3").is_file()


@pytest.mark.parametrize("path", ["/", "/app.js", "/api/facts", "/api/egress"])
def test_public_content_does_not_challenge_for_login(setup, path):
    with TestClient(create_app()) as client:
        response = client.get(path)
        assert response.status_code == 200
        assert "www-authenticate" not in response.headers
        # Old browser credentials do not restore a login requirement.
        assert client.get(path, headers={"Authorization": "Basic invalid!!!"}).status_code == 200


def test_chat_is_disabled_even_with_model_key(setup, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "dummy-not-a-real-key")
    with TestClient(create_app()) as client:
        response = client.post("/api/ask", json={"question": "Who owns billing?"})
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"]


def test_public_egress_still_returns_the_log(setup):
    from chronicle.web import get_logger

    get_logger().log(provider="fixture", model="offline", redacted=True,
                     request_preview="Who owns ORG_1?")
    with TestClient(create_app()) as client:
        response = client.get("/api/egress")
        assert response.status_code == 200
        assert response.json()[0]["request_preview"] == "Who owns ORG_1?"


@pytest.mark.parametrize("cap", ["0", "-1", "nan", "inf"])
def test_enabled_chat_requires_a_finite_positive_budget(setup, monkeypatch, cap):
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", cap)
    with pytest.raises(ValueError, match="CHRONICLE_SPEND_LIMIT_USD"):
        create_app()


def test_enabled_chat_requires_credentials(setup, monkeypatch):
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "1")
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        create_app()


def test_chat_limit_and_cross_site_guard_before_answering(setup, monkeypatch):
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "1")
    monkeypatch.setenv("NEBIUS_API_KEY", "dummy-not-a-real-key")
    monkeypatch.setenv("CHRONICLE_WEB_ASKS_PER_MINUTE", "1")
    answer = Mock(return_value=AnswerResult("Maya Patel", ["demo-1"]))
    monkeypatch.setattr("chronicle.memory.server.answer_question", answer)
    with TestClient(create_app()) as client:
        question = {"question": "Who owns billing?"}
        assert client.post("/api/ask", json=question,
                           headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        assert client.post("/api/ask", json=question).json()["answer"] == "Maya Patel"
        response = client.post("/api/ask", json=question)
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"
        answer.assert_called_once()


def test_empty_memory_is_healthy_while_waiting_for_state(setup):
    (setup / "claims.jsonl").unlink()
    with TestClient(create_app()) as client:
        assert client.get("/healthz").json() == {"status": "ok", "memory_loaded": False}
        assert client.get("/api/facts").json() == []


def test_import_loads_topic_pages_without_a_database_backup(setup):
    page = {"kind": "topic", "page_id": "topic_billing", "title": "Billing owner",
            "current": "Maya Patel", "valid_from": "2026-05-01",
            "content": "TOPIC: Billing owner\nMaya Patel owns billing.",
            "sources": [{"doc_id": "demo-1", "quote": "Maya Patel owns billing.",
                         "observed_at": "2026-05-01"}]}
    (setup / "pages.jsonl").write_text(json.dumps(page) + "\n", encoding="utf-8")
    with TestClient(create_app()) as client:
        facts = client.get("/api/facts").json()
        assert {f["kind"] for f in facts} == {"claim", "topic"}


def test_overlapping_questions_do_not_start_another_answer(setup, monkeypatch):
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "1")
    monkeypatch.setenv("NEBIUS_API_KEY", "dummy-not-a-real-key")
    entered, release = threading.Event(), threading.Event()

    def answer(*args, **kwargs):
        entered.set()
        assert release.wait(5), "test did not release the first question"
        return AnswerResult("Maya Patel", ["demo-1"])

    model = Mock(side_effect=answer)
    monkeypatch.setattr("chronicle.memory.server.answer_question", model)
    with TestClient(create_app()) as client, ThreadPoolExecutor(max_workers=1) as pool:
        question = {"question": "Who owns billing?"}
        first = pool.submit(client.post, "/api/ask", json=question)
        try:
            assert entered.wait(5)
            assert client.post("/api/ask", json=question).status_code == 429
        finally:
            release.set()
        assert first.result(timeout=5).status_code == 200
        model.assert_called_once()


def test_ephemeral_hosting_cannot_enable_paid_chat(setup, monkeypatch):
    monkeypatch.setenv("CHRONICLE_WEB_EPHEMERAL", "1")
    monkeypatch.setenv("CHRONICLE_WEB_CHAT_ENABLED", "1")
    with pytest.raises(ValueError, match="spending logs reset"):
        create_app()


def test_configured_snapshot_is_loaded_before_opening_memory(setup, monkeypatch):
    restore = Mock(return_value=setup)
    monkeypatch.setattr("chronicle.web.restore_snapshot", restore)
    monkeypatch.setenv("CHRONICLE_STATE_SNAPSHOT_URL", "https://files.example/state.zip")
    monkeypatch.setenv("CHRONICLE_STATE_SNAPSHOT_SHA256", "0" * 64)
    with TestClient(create_app()) as client:
        assert client.get("/healthz").json()["memory_loaded"] is True
    restore.assert_called_once_with(setup, "https://files.example/state.zip", "0" * 64)


def test_public_config_reports_chat_and_source_dates_without_secrets(setup, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "not-for-the-browser")
    docs = [{"doc_id": "d1", "date": "2027-07-20", "text": "First source"},
            {"doc_id": "d2", "date": "2027-09-24", "text": "Last source"}]
    (setup / "docs.jsonl").write_text("\n".join(json.dumps(d) for d in docs), encoding="utf-8")
    with TestClient(create_app()) as client:
        response = client.get("/api/config")
        assert response.json() == {"chat_enabled": False, "document_count": 2,
                                   "corpus_start": "2027-07-20", "corpus_end": "2027-09-24"}
        assert "not-for-the-browser" not in response.text
