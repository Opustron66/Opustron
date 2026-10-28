import pytest


@pytest.fixture(autouse=True)
def no_query_llm(monkeypatch):
    """Retrieval tests patch the answer LLM; keep the query-understanding call out of them."""
    monkeypatch.setenv("CHRONICLE_QUERY_LLM", "off")
