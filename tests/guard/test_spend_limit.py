from types import SimpleNamespace

import pytest

from chronicle.guard import egress_logger, llm_client, spend_limit
from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.llm_client import LLMClient
from chronicle.guard.spend_limit import SpendLimitReached

ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"


@pytest.fixture
def log(tmp_path, monkeypatch):
    logger = EgressLogger(tmp_path / "egress.log")
    monkeypatch.setattr(egress_logger, "_default_logger", logger)
    monkeypatch.setattr(llm_client, "_CACHE_DIR", tmp_path / "cache")
    (tmp_path / "cache").mkdir()
    for var in ("CHRONICLE_SPEND_LIMIT_USD", "CHRONICLE_SPEND_SINCE"):
        monkeypatch.delenv(var, raising=False)
    return logger


def client(calls, model=ULTRA, use_cache=False):
    def transport(**kw):
        calls.append(kw)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="ok"), finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=400_000, completion_tokens=100_000),  # $0.70 on Ultra
        )
    return LLMClient(api_key="k", default_model=model, use_cache=use_cache, transport=transport)


def ask(c, text="hi"):
    return c.complete([{"role": "user", "content": text}])


def test_prices_match_token_factory():
    assert spend_limit.cost_usd(ULTRA, 1_000_000, 1_000_000) == pytest.approx(4.00)
    assert spend_limit.cost_usd("nvidia/Nemotron-3_5-Lightning", 1_000_000, 1_000_000) == pytest.approx(0.30)
    assert spend_limit.cost_usd("some/unknown-model", 1_000_000, 0) == pytest.approx(1.00)


def test_no_limit_means_no_check(log):
    calls = []
    c = client(calls)
    for _ in range(5):
        ask(c)
    assert len(calls) == 5


def test_calls_stop_once_the_limit_is_reached(log, monkeypatch):
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "1.00")
    calls = []
    c = client(calls)
    ask(c)  # $0.70 spent
    ask(c)  # $1.40 spent: this one was allowed because $0.70 < $1.00 beforehand
    with pytest.raises(SpendLimitReached, match=r"\$1\.40 of \$1\.00"):
        ask(c)
    assert len(calls) == 2  # the refused call never reached the transport


def test_only_spend_after_since_counts(log, monkeypatch):
    log.log(provider="nebius_token_factory", model=ULTRA, prompt_tokens=10_000_000, redacted=False)
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "1.00")
    calls = []
    with pytest.raises(SpendLimitReached):
        ask(client(calls))
    monkeypatch.setenv("CHRONICLE_SPEND_SINCE", "2999-01-01")
    ask(client(calls))
    assert len(calls) == 1


def test_cache_hits_are_free_and_still_served_at_the_limit(log, monkeypatch):
    calls = []
    c = client(calls, use_cache=True)
    ask(c, "same question")
    monkeypatch.setenv("CHRONICLE_SPEND_LIMIT_USD", "0.10")
    assert ask(c, "same question") == "ok"  # answered from cache, nothing sent
    with pytest.raises(SpendLimitReached):
        ask(c, "a new question")
    assert len(calls) == 1


def test_tavily_and_cached_records_do_not_count():
    records = [
        {"provider": "tavily", "model": "search", "prompt_tokens": 0, "completion_tokens": 0, "ts": "2026"},
        {"provider": "nebius_token_factory", "model": ULTRA, "prompt_tokens": 1_000_000,
         "completion_tokens": 0, "cached": True, "ts": "2026"},
    ]
    assert spend_limit.spent_usd(records) == 0
