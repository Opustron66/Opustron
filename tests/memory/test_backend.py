import threading
from datetime import UTC, datetime

from chronicle.integrations.hermes_provider import ChronicleMemoryProvider
from chronicle.integrations.tavily import TavilyClient
from chronicle.memory.backend import SQLiteBackend, default_db_path

from .conftest import make_claim


def _day(d: str) -> datetime:
    return datetime.fromisoformat(d).replace(tzinfo=UTC)


def test_as_of_returns_fact_true_at_that_date():
    backend = SQLiteBackend(":memory:")
    old = backend.remember("Alice owns payments", source="test", occurred_at=_day("2026-05-01"))
    backend.remember("Bob owns payments", source="test", occurred_at=_day("2026-05-15"), supersedes=old)

    before = backend.recall("payments owner", as_of=_day("2026-05-10"))
    after = backend.recall("payments owner", as_of=_day("2026-05-20"))

    assert [r.content for r in before] == ["Alice owns payments"]
    assert before[0].valid_to == _day("2026-05-15")
    assert [r.content for r in after] == ["Bob owns payments"]


def test_replace_and_remove_through_hermes_provider():
    provider = ChronicleMemoryProvider(backend=SQLiteBackend(":memory:"), web=TavilyClient(api_key=""))
    provider.initialize("s1")
    provider.on_memory_write("add", "memory", "User prefers tea")
    provider.on_memory_write("replace", "memory", "User prefers coffee", {"previous_content": "User prefers tea"})
    block = provider.prefetch("what does the user prefer")
    assert "coffee" in block and "tea" not in block
    provider.on_memory_write("remove", "memory", "User prefers coffee")
    assert provider.prefetch("what does the user prefer") == ""


def test_memory_survives_restart(tmp_path):
    path = tmp_path / "memory.sqlite3"
    first = SQLiteBackend(path)
    first.remember("Carol joined the platform team", source="hermes://s1")
    first.close()
    second = SQLiteBackend(path)
    assert [r.content for r in second.recall("platform team")] == ["Carol joined the platform team"]
    assert second.recall("platform team")[0].source == "hermes://s1"


def test_recall_includes_ingested_claims_with_day_dates():
    backend = SQLiteBackend(":memory:")
    backend.api.ingest_claims([make_claim("Alice Chen", "owns", "payments service", observed="2026-04-16")])
    (hit,) = backend.recall("payments", as_of=_day("2026-05-01"))
    assert hit.content == "Alice Chen owns payments service"
    assert hit.valid_from == _day("2026-04-16")


def test_concurrent_writes_from_threads():
    backend = SQLiteBackend(":memory:")
    threads = [threading.Thread(target=backend.remember, args=(f"fact {i} about atlas",), kwargs={"source": "t"})
               for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(backend.recall("atlas", limit=50)) == 20


def test_default_path_honours_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CHRONICLE_MEMORY_DB", str(tmp_path / "x.sqlite3"))
    assert default_db_path() == tmp_path / "x.sqlite3"
    monkeypatch.delenv("CHRONICLE_MEMORY_DB")
    assert default_db_path().name == "memory.sqlite3"
