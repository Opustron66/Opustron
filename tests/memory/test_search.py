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


def test_rrf_rewards_items_ranked_well_in_several_channels():
    from chronicle.memory.search import rrf
    fused = rrf([["a", "b", "c"], ["c", "b"], ["b"]])
    assert sorted(fused, key=fused.get, reverse=True) == ["b", "c", "a"]
    assert fused["a"] == 1 / 61


def test_document_chunks_split_long_docs_and_filter_by_date():
    from datetime import date

    from chronicle.memory.search import chunk_documents, rank_chunks
    rows = [{"doc_id": "S:a", "date": "2027-07-01", "text": "Channel: #site\n" + "\n".join(["pour moved"] * 400)},
            {"doc_id": "E:b", "date": "2027-08-01", "text": "Subject: pour\nThe pour moved to 2 Sep."}]
    chunks = chunk_documents(rows, max_chars=500)
    assert len([c for c in chunks if c.doc_id == "S:a"]) > 1
    assert all(c.text.startswith("Channel: #site") for c in chunks if c.doc_id == "S:a")
    assert {c.doc_id for c, _ in rank_chunks(chunks, "pour moved", until=date(2027, 7, 15))} == {"S:a"}
