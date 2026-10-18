import json
from types import SimpleNamespace

import pytest

from chronicle.guard import egress_logger, llm_client
from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.llm_client import LLMClient

MESSAGES = [{"role": "user", "content": "Synthetic cache regression"}]
SCHEMA = {"type": "object", "properties": {"claims": {"type": "array"}}, "required": ["claims"]}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_client, "_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(egress_logger, "_default_logger", EgressLogger(tmp_path / "egress.log"))


def response(content, finish="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish)],
                           usage=SimpleNamespace(prompt_tokens=3, completion_tokens=5))


def test_empty_reply_does_not_poison_larger_budget_retry():
    calls = []
    def transport(**kw):
        calls.append(kw["max_tokens"])
        return response("" if len(calls) == 1 else '{"claims": []}')
    client = LLMClient(transport=transport)
    with pytest.raises(ValueError, match="empty response"):
        client.complete(MESSAGES, schema=SCHEMA, max_tokens=8192)
    assert not list(llm_client._CACHE_DIR.glob("*.txt"))
    assert client.complete(MESSAGES, schema=SCHEMA, max_tokens=16384) == {"claims": []}
    assert calls == [8192, 16384]


@pytest.mark.parametrize("bad", ["", "{broken", '{"wrong": []}', '{"claims": null}', '{"claims": "oops"}'])
def test_invalid_existing_entry_is_bypassed_and_replaced(bad):
    calls = []
    def transport(**kw):
        calls.append(kw)
        return response('{"claims": []}')
    client = LLMClient(transport=transport)
    client._save_cache(client._cache_key(MESSAGES, SCHEMA, client.model), bad)
    assert client.complete(MESSAGES, schema=SCHEMA) == {"claims": []}
    assert client.complete(MESSAGES, schema=SCHEMA) == {"claims": []}
    assert len(calls) == 1


@pytest.mark.parametrize("wrapped", [False, True])
def test_malformed_json_is_not_cached(wrapped):
    client = LLMClient(transport=lambda **kw: response("{broken"))
    schema = {"name": "claims", "schema": SCHEMA} if wrapped else SCHEMA
    if wrapped:
        assert client.complete(MESSAGES, schema=schema) == "{broken"  # caller retains raw-reply contract
    else:
        with pytest.raises(ValueError):
            client.complete(MESSAGES, schema=schema)
    assert not list(llm_client._CACHE_DIR.glob("*.txt"))


def test_settings_isolate_responses_but_identical_requests_hit_cache():
    calls = []
    def transport(**kw):
        calls.append(kw)
        return response("ok")
    client = LLMClient(transport=transport, base_url="https://first.example/v1", max_tokens=8192)
    client.complete(MESSAGES)
    client.complete(MESSAGES)
    client.complete(MESSAGES, max_tokens=16384)
    client.complete(MESSAGES, temperature=0.5)
    LLMClient(transport=transport, base_url="https://second.example/v1", max_tokens=8192).complete(MESSAGES)
    assert len(calls) == 4


@pytest.mark.parametrize("finish", ["length", "content_filter"])
def test_incomplete_reply_is_logged_but_not_cached(finish, tmp_path):
    client = LLMClient(transport=lambda **kw: response('{"claims": []}', finish))
    with pytest.raises(ValueError, match=f"finish_reason={finish}"):
        client.complete(MESSAGES, SCHEMA)
    assert not list(llm_client._CACHE_DIR.glob("*.txt"))
    logged = json.loads((tmp_path / "egress.log").read_text())
    assert logged["completion_tokens"] == 5


def test_cache_stores_tokens_not_restored_email():
    calls = []
    def transport(**kw):
        calls.append(kw)
        return response("EMAIL_1")
    client = LLMClient(transport=transport)
    messages = [{"role": "user", "content": "Reply to maya@example.test"}]
    assert client.complete(messages) == client.complete(messages) == "maya@example.test"
    assert len(calls) == 1
    cached = next(llm_client._CACHE_DIR.glob("*.txt")).read_text()
    assert cached == "EMAIL_1"
    assert "maya@example.test" not in json.dumps(calls)
