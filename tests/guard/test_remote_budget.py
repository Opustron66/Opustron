"""Execute the actual Lua against a local Redis emulator. No remote credentials."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import fakeredis
import httpx
import pytest

from chronicle.guard import remote_budget as rb
from chronicle.guard.llm_client import LLMClient
from chronicle.guard.spend_limit import SpendLimitReached


@pytest.fixture
def ledger(monkeypatch):
    for key, value in {
        "CHRONICLE_SPEND_BACKEND": "upstash", "CHRONICLE_MODEL": rb.MODEL,
        "CHRONICLE_SPEND_LIMIT_USD": "0.25", "CHRONICLE_SPEND_BUDGET_ID": "demo-v1",
        "UPSTASH_REDIS_REST_URL": "https://test.upstash.io",
        "UPSTASH_REDIS_REST_TOKEN": "fake-token", "CHRONICLE_LLM_CACHE": "0",
    }.items():
        monkeypatch.setenv(key, value)
    redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(rb.RemoteBudget, "command", lambda self, *args: redis.execute_command(*args))
    budget = rb.RemoteBudget()
    budget.initialize()
    return budget, redis


def response(prompt=2000, completion=500):
    return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion),
                           choices=[SimpleNamespace(message=SimpleNamespace(content="Saved answer"), finish_reason="stop")])


def test_budget_survives_new_instances_and_cannot_be_reinitialized(ledger):
    budget, _ = ledger
    receipt = budget.reserve(rb.MODEL, 4096)
    budget.settle(receipt, 2000, 500)
    assert rb.RemoteBudget().status()["spent_or_reserved_microusd"] == 240
    with pytest.raises(rb.BudgetUnavailable, match="already exists"):
        rb.RemoteBudget().initialize()


def test_concurrent_reservations_cannot_overspend(ledger):
    budget, _ = ledger
    def reserve(_):
        try:
            return budget.reserve(rb.MODEL, 4096)
        except SpendLimitReached:
            return None
    with ThreadPoolExecutor(max_workers=10) as pool:
        receipts = list(pool.map(reserve, range(20)))
    assert sum(r is not None for r in receipts) == 3
    assert 0 < budget.status()["spent_or_reserved_microusd"] <= 250_000


def test_settlement_is_once_only_and_refunds_unused_reservation(ledger):
    budget, _ = ledger
    receipt = budget.reserve(rb.MODEL, 4096)
    budget.settle(receipt, 2000, 500)
    with pytest.raises(rb.BudgetUnavailable):
        budget.settle(receipt, 2000, 500)
    assert budget.status()["spent_or_reserved_microusd"] == 240


@pytest.mark.parametrize("corruption", ["missing", "negative", "expire", "limit", "version"])
def test_missing_or_corrupt_ledger_blocks_calls(ledger, corruption):
    budget, redis = ledger
    if corruption == "missing":
        redis.delete(budget.key)
    elif corruption == "expire":
        redis.expire(budget.key, 100)
    else:
        redis.hset(budget.key, {"negative": "spent", "limit": "limit", "version": "version"}[corruption], -1)
    with pytest.raises(rb.BudgetUnavailable):
        budget.reserve(rb.MODEL, 4096)
    with pytest.raises(rb.BudgetUnavailable):
        budget.status()


def test_timeout_keeps_reservation_and_never_retries_transport(ledger):
    budget, _ = ledger
    transport = Mock(side_effect=TimeoutError("provider may have processed request"))
    client = LLMClient(api_key="fake", transport=transport, use_cache=False, max_tokens=4096)
    with pytest.raises(TimeoutError):
        client.complete([{"role": "user", "content": "Who owns billing?"}])
    transport.assert_called_once()
    assert budget.status()["spent_or_reserved_microusd"] == rb.token_cost(rb.CONTEXT_TOKENS, 4096)


def test_schema_fallback_reserves_each_transport_attempt(ledger):
    budget, _ = ledger
    class Rejected(Exception):
        status_code = 400
    transport = Mock(side_effect=[Rejected("response_format json_schema unsupported"), response()])
    client = LLMClient(api_key="fake", transport=transport, use_cache=False, max_tokens=4096)
    client.complete([{"role": "user", "content": "Who owns billing?"}], schema={"name": "test", "schema": {}})
    assert transport.call_count == 2
    assert budget.status()["spent_or_reserved_microusd"] == rb.token_cost(rb.CONTEXT_TOKENS, 4096) + 240


def test_network_error_in_budget_prevents_model_transport(ledger, monkeypatch):
    transport = Mock()
    def offline(*args):
        raise rb.BudgetUnavailable("offline")
    monkeypatch.setattr(rb.RemoteBudget, "command", offline)
    with pytest.raises(rb.BudgetUnavailable):
        LLMClient(api_key="fake", transport=transport, use_cache=False).complete([{"role": "user", "content": "hello"}])
    transport.assert_not_called()


def test_exhausted_allowance_blocks_transport(ledger):
    budget, _ = ledger
    for _ in range(3):
        budget.reserve(rb.MODEL, 4096)
    transport = Mock()
    with pytest.raises(SpendLimitReached):
        LLMClient(api_key="fake", transport=transport, use_cache=False, max_tokens=4096).complete(
            [{"role": "user", "content": "hello"}])
    transport.assert_not_called()


def test_cached_answer_needs_no_remote_reservation(ledger, monkeypatch, tmp_path):
    from chronicle.guard import llm_client

    monkeypatch.setenv("CHRONICLE_LLM_CACHE", "1")
    monkeypatch.setattr(llm_client, "_CACHE_DIR", tmp_path)
    transport = Mock(return_value=response())
    client = LLMClient(api_key="fake", transport=transport)
    messages = [{"role": "user", "content": "hello"}]
    assert client.complete(messages) == "Saved answer"
    monkeypatch.setattr(rb.RemoteBudget, "command", Mock(side_effect=AssertionError("No budget request on cache hit")))
    assert client.complete(messages) == "Saved answer"
    transport.assert_called_once()


def test_successful_response_settles_actual_cost(ledger):
    budget, _ = ledger
    assert LLMClient(api_key="fake", transport=Mock(return_value=response()), use_cache=False).complete(
        [{"role": "user", "content": "hello"}]) == "Saved answer"
    assert budget.status()["spent_or_reserved_microusd"] == 240


def test_missing_usage_keeps_reservation(ledger):
    budget, _ = ledger
    reply = response()
    reply.usage = None
    with pytest.raises(rb.BudgetUnavailable, match="usage"):
        LLMClient(api_key="fake", transport=Mock(return_value=reply), use_cache=False, max_tokens=4096).complete(
            [{"role": "user", "content": "hello"}])
    assert budget.status()["spent_or_reserved_microusd"] == rb.token_cost(rb.CONTEXT_TOKENS, 4096)


def test_wrong_model_cannot_spend(ledger):
    with pytest.raises(rb.BudgetUnavailable):
        ledger[0].reserve("some/other-model", 4096)


def test_raise_to_five_dollars_preserves_spending_and_inflight_requests(ledger):
    budget, redis = ledger
    settled = budget.reserve(rb.MODEL, 4096)
    budget.settle(settled, 2000, 500)
    pending = budget.reserve(rb.MODEL, 4096)
    before = budget.status()["spent_or_reserved_microusd"]
    budget.raise_limit("5")
    assert budget.status() == {"limit_microusd": 5_000_000, "spent_or_reserved_microusd": before}
    assert redis.hexists(budget.key, pending)
    budget.settle(pending, 2000, 500)
    assert budget.status()["spent_or_reserved_microusd"] == 480


def test_stale_configuration_cannot_raise_again_or_spend(ledger):
    budget, _ = ledger
    stale = rb.RemoteBudget()
    budget.raise_limit("5")
    with pytest.raises(rb.BudgetUnavailable):
        stale.reserve(rb.MODEL, 4096)
    with pytest.raises(rb.BudgetUnavailable):
        stale.raise_limit("10")
    assert budget.status()["limit_microusd"] == 5_000_000


@pytest.mark.parametrize("target", ["0.25", "0.1", "0", "nan"])
def test_raise_cannot_decrease_or_reset_budget(ledger, target):
    budget, _ = ledger
    with pytest.raises(rb.BudgetUnavailable):
        budget.raise_limit(target)
    assert budget.status()["limit_microusd"] == 250_000


def test_ultra_reservations_and_settlement_use_ultra_prices(ledger, monkeypatch):
    budget, _ = ledger
    budget.raise_limit("5")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "5")
    monkeypatch.setenv("CHRONICLE_MODEL", rb.ULTRA)
    transport = Mock(return_value=response())
    assert LLMClient(api_key="fake", transport=transport, use_cache=False).complete(
        [{"role": "user", "content": "hello"}]) == "Saved answer"
    assert transport.call_args.kwargs["model"] == rb.ULTRA
    assert budget.status()["spent_or_reserved_microusd"] == 3500
    receipt = budget.reserve(rb.ULTRA, 16_384)
    assert budget.status()["spent_or_reserved_microusd"] == 3500 + 1_097_728
    budget.settle(receipt, 2000, 500)
    assert budget.status()["spent_or_reserved_microusd"] == 7000


def test_settlement_uses_reserved_model_even_if_default_is_different(ledger):
    budget, _ = ledger
    budget.raise_limit("5")
    receipt = budget.reserve(rb.ULTRA, 4096)
    budget.settle(receipt, 2000, 500)
    assert budget.status()["spent_or_reserved_microusd"] == 3500


def test_raise_cli_reports_new_limit_without_resetting_spent(ledger, monkeypatch, capsys):
    budget, _ = ledger
    receipt = budget.reserve(rb.MODEL, 4096)
    budget.settle(receipt, 2000, 500)
    monkeypatch.setattr("sys.argv", ["chronicle.budget", "raise-limit", "--to", "5"])
    rb.main()
    assert '"limit_microusd": 5000000' in capsys.readouterr().out


def test_raise_does_not_recreate_a_deleted_ledger(ledger):
    budget, redis = ledger
    redis.delete(budget.key)
    with pytest.raises(rb.BudgetUnavailable):
        budget.raise_limit("5")
    assert not redis.exists(budget.key)


def test_sdk_retries_are_disabled_for_remote_budget(ledger, monkeypatch):
    constructor = Mock(return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=Mock()))))
    monkeypatch.setattr("openai.OpenAI", constructor)
    LLMClient(api_key="fake", use_cache=False)._get_transport()
    assert constructor.call_args.kwargs["max_retries"] == 0


def test_http_errors_hide_credentials(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "very-secret")
    monkeypatch.setenv("CHRONICLE_SPEND_BUDGET_ID", "demo-v1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "0.25")
    monkeypatch.setenv("CHRONICLE_MODEL", rb.MODEL)
    monkeypatch.setattr(httpx.Client, "post", Mock(side_effect=httpx.ConnectError("very-secret")))
    with pytest.raises(rb.BudgetUnavailable, match="Budget service unavailable") as exc:
        rb.RemoteBudget().status()
    assert "very-secret" not in str(exc.value)


@pytest.mark.parametrize("value", ["0", "nan", "inf", "-1", "abc", "0.0000001"])
def test_budget_must_be_finite_positive_microdollars(value):
    with pytest.raises(rb.BudgetUnavailable):
        rb.micros(value)


def test_budget_commands_reuse_connections_without_replaying_requests(monkeypatch):
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "fake-secret")
    monkeypatch.setenv("CHRONICLE_SPEND_BUDGET_ID", "demo-v1")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "5")
    monkeypatch.setenv("CHRONICLE_MODEL", rb.ULTRA)
    client = Mock()
    client.post.return_value = httpx.Response(200, json={"result": 1}, request=httpx.Request("POST", "https://test.upstash.io"))
    constructor = Mock(return_value=client)
    monkeypatch.setattr(httpx, "Client", constructor)
    rb._http_client.cache_clear()
    try:
        first, second = rb.RemoteBudget(), rb.RemoteBudget()
        assert first.command("PING") == 1
        assert second.command("PTTL", second.key) == 1
        constructor.assert_called_once()
        assert client.post.call_count == 2
        assert client.post.call_args_list[0].kwargs["json"] == ["PING"]
        assert client.post.call_args_list[1].kwargs["json"] == ["PTTL", second.key]
        assert client.post.call_args.kwargs["headers"] == {"Authorization": "Bearer fake-secret"}
    finally:
        rb._http_client.cache_clear()
