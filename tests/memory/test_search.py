from chronicle.memory.search import tokens


def test_tokens_drop_stopwords_and_plurals():
    assert tokens("Who owns the Payments services?") == ["owns", "payment", "service"]


def test_search_ranks_matching_fact_first(memory, payments, claim):
    memory.ingest_claims([*payments, claim("Priya", "works_on", "search ranking", observed="2026-04-20")])
    hits = memory.search("who owns the payments service")
    assert {h.fact.subject for h in hits[:2]} == {"Alice Chen", "Dana Lee"}
    assert all(h.score > 0 for h in hits)


def test_search_as_of_hides_facts_not_true_then(memory, payments):
    memory.ingest_claims(payments)
    assert [h.fact.subject for h in memory.search("payments owner", as_of="2026-05-03")] == ["Alice Chen"]
    assert [h.fact.subject for h in memory.search("payments owner", as_of="2026-05-20")] == ["Dana Lee"]


def test_search_matches_source_quote_words(memory, payments):
    memory.ingest_claims(payments)
    hits = memory.search("takes over effective today")
    assert hits and {h.fact.subject for h in hits} >= {"Dana Lee"}


def test_search_without_terms_returns_nothing(memory, payments):
    memory.ingest_claims(payments)
    assert memory.search("who is the") == []
    assert memory.search("zebra") == []


def test_search_limit(memory, claim):
    memory.ingest_claims([claim(f"P{i}", "works_on", "atlas", observed="2026-04-16") for i in range(20)])
    assert len(memory.search("atlas", k=5)) == 5
