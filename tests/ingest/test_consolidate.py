import json

from chronicle.ingest.consolidate import (Update, blocks, build_topics, consolidate, discover, merge_names,
                                          validate_entries)
from chronicle.ingest.extractor import _squash
from chronicle.memory import MemoryAPI


class ScriptedLLM:
    """Answers discovery calls per document and merge calls with fixed groups."""

    def __init__(self, updates_by_doc, groups=None):
        self.updates_by_doc, self.groups, self.calls = updates_by_doc, groups or [], []

    def complete(self, messages, schema=None):
        self.calls.append(schema["name"])
        if schema["name"] == "groups":
            listing = dict(line.split(": ", 1) for line in messages[1]["content"].splitlines())
            ids = {name: int(i) for i, name in listing.items()}
            return json.dumps({"groups": [{"name": g[0], "members": [ids[n] for n in g if n in ids]}
                                          for g in self.groups]})
        for marker, updates in self.updates_by_doc.items():
            if marker in messages[1]["content"]:
                return json.dumps({"updates": updates})
        return json.dumps({"updates": []})


DOCS = [
    {"doc_id": "S:site@2027-07-01", "date": "2027-07-01", "text": "Ravi: camden day to day stays with Ravi for now."},
    {"doc_id": "E:2027-07-20", "date": "2027-07-20",
     "text": "Subject: handover\nFrom Monday Priya Nair takes Camden Row site-side oversight."},
]


def test_merge_groups_names_for_the_same_topic():
    names = ["Camden Row - site-side day-to-day lead", "camden day to day", "Harbor Point steel - ETA"]
    llm = ScriptedLLM({}, groups=[["Camden Row - site-side day-to-day lead", "camden day to day"]])
    canon = merge_names(names, llm, model="m", cache=None)
    assert canon["camden day to day"] == "Camden Row - site-side day-to-day lead"
    assert canon["Harbor Point steel - ETA"] == "Harbor Point steel - ETA"


def test_blocks_put_names_sharing_a_rare_word_together():
    names = ["camden day to day", "Camden Row lead", "steel ETA", "harbor steel delivery", "lonely"]
    batches = blocks(names)
    together = [set(b) for b in batches]
    assert any({0, 1} <= b for b in together) and any({2, 3} <= b for b in together)
    assert all(4 not in b for b in together)


def test_discover_keeps_only_verbatim_quotes_and_resolves_dates():
    llm = ScriptedLLM({"Priya Nair": [
        {"topic": "Camden Row - site lead", "value": "Priya Nair", "effective": "Monday",
         "quote": "From Monday Priya Nair takes Camden Row site-side oversight."},
        {"topic": "Camden Row - site lead", "value": "Ravi", "quote": "Ravi keeps it."},  # not in doc
    ]})
    updates, dropped = discover(DOCS[1], llm, model="m", cache=None)
    assert dropped == 1 and [u.value for u in updates] == ["Priya Nair"]
    assert updates[0].effective == "2027-07-26" and updates[0].stated == "2027-07-20"


def test_timeline_entries_must_cite_a_known_document_verbatim():
    docs = {d["doc_id"]: _squash(d["text"]) for d in DOCS}
    good = Update("t", "Ravi", "camden day to day stays with Ravi", "S:site@2027-07-01", "2027-07-01")
    wrong_doc = Update("t", "Ravi", "camden day to day stays with Ravi", "E:nope", "2027-07-01")
    not_verbatim = Update("t", "Priya", "Priya runs Camden", "E:2027-07-20", "2027-07-20")
    assert validate_entries([good, wrong_doc, not_verbatim], docs) == [good]


def test_consolidate_writes_one_timeline_per_merged_topic_and_p2_loads_it(tmp_path):
    (tmp_path / "docs.jsonl").write_text("".join(json.dumps(d) + "\n" for d in DOCS))
    llm = ScriptedLLM({
        "Ravi:": [{"topic": "camden day to day", "value": "Ravi",
                   "quote": "camden day to day stays with Ravi for now."}],
        "Priya Nair": [{"topic": "Camden Row - site-side day-to-day lead", "value": "Priya Nair",
                        "effective": "Monday", "quote": "Priya Nair takes Camden Row site-side oversight"}],
    }, groups=[["Camden Row - site-side day-to-day lead", "camden day to day"]])
    stats = consolidate(tmp_path, llm, model="m", workers=1)
    pages = [json.loads(line) for line in (tmp_path / "pages.jsonl").read_text().splitlines()]
    assert stats.topics == 1 and len(pages) == 1
    page = pages[0]
    assert page["current"] == "Priya Nair" and page["aliases"] == ["camden day to day"]
    assert page["content"].index("Ravi") < page["content"].index("Priya Nair")
    assert "VALUES IN ORDER: Ravi -> Priya Nair" in page["content"]

    # Cached: a second pass makes no LLM calls.
    calls = len(llm.calls)
    consolidate(tmp_path, llm, model="m", workers=1)
    assert len(llm.calls) == calls

    with MemoryAPI.from_state(tmp_path) as memory:
        hits = memory.search("who leads camden day to day", kind="topic")
        assert [h.fact.subject for h in hits] == ["Camden Row - site-side day-to-day lead"]
        assert {s.doc_id for s in hits[0].fact.sources} == {d["doc_id"] for d in DOCS}
    with MemoryAPI.from_state(tmp_path) as memory:  # re-sync is a no-op
        assert len(memory.facts(kind="topic")) == 1


def test_sync_pages_revises_changed_pages_and_retires_missing_ones():
    memory = MemoryAPI()
    page = {"kind": "topic", "page_id": "topic_a", "title": "A", "current": "1", "valid_from": "2027-01-01",
            "content": "TOPIC: A\n- 2027-01-01 [D1]: 1", "sources": [{"doc_id": "D1", "quote": "q",
                                                                     "observed_at": "2027-01-01"}]}
    assert memory.database.sync_pages([page])["added"] == 1
    assert memory.database.sync_pages([page])["unchanged"] == 1
    assert memory.database.sync_pages([{**page, "current": "2"}])["revised"] == 1
    assert [f.object for f in memory.facts(kind="topic")] == ["2"]
    assert memory.database.sync_pages([])["retired"] == 1
    assert memory.facts(kind="topic") == []
