import json
from datetime import date
from unittest.mock import MagicMock, patch

from chronicle.reason import pipeline
from chronicle.reason.answerer import corpus_messages, generate_corpus_answer
from chronicle.reason.models import AnswerResult, Evidence, QueryPlan
from chronicle.reason.retriever import corpus_evidence

CORPUS = [Evidence("E:a", "Beacon at 25%.", "2026-05-01"), Evidence("E:b", "Beacon hit 50%.", "2026-05-14")]


def test_corpus_evidence_is_every_document_oldest_first(tmp_path):
    rows = [{"doc_id": "E:late", "date": "2026-05-14", "text": "late"},
            {"doc_id": "E:early", "date": "2026-05-01", "text": "early"}]
    (tmp_path / "docs.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    assert [e.doc_id for e in corpus_evidence(tmp_path)] == ["E:early", "E:late"]
    assert corpus_evidence(None) == [] and corpus_evidence(tmp_path / "missing") == []


def test_prompt_prefix_is_the_same_for_every_question_so_it_can_be_cached():
    plain = corpus_messages(QueryPlan("Who owns payments?"), CORPUS)
    as_of = corpus_messages(QueryPlan("As of 2026-05-10, had Beacon reached 50%?", kind="as_of",
                                      reference_date=date(2026, 5, 10)), CORPUS)
    ordered = corpus_messages(QueryPlan("Put these in the order they happened, earliest first: a; b"), CORPUS)
    assert plain[0] == as_of[0] == ordered[0]
    corpus_text = plain[1]["content"].split("QUESTION:")[0].split("\n\n" + "Answer as of")[0]
    assert as_of[1]["content"].startswith(corpus_text.rstrip())
    assert "Answer as of 2026-05-10" in as_of[1]["content"] and "earliest first" in ordered[1]["content"]
    assert plain[1]["content"].endswith("QUESTION: Who owns payments?")


def test_generate_corpus_answer_keeps_only_real_citations():
    with patch("chronicle.reason.answerer.llm.complete",
               return_value={"answer": "50%", "source_ids": ["E:b", "E:made-up"]}):
        assert generate_corpus_answer(QueryPlan("Beacon?"), CORPUS) == AnswerResult("50%", ["E:b"])
    with patch("chronicle.reason.answerer.llm.complete") as complete:
        assert generate_corpus_answer(QueryPlan("Beacon?"), []) == AnswerResult("Not in the corpus", [])
    complete.assert_not_called()


def test_pipeline_uses_whole_corpus_only_when_switched_on(monkeypatch):
    def run():
        with patch.object(pipeline, "open_state", return_value=MagicMock()), \
             patch.object(pipeline, "understand", side_effect=lambda plan: plan), \
             patch.object(pipeline, "corpus_evidence", return_value=CORPUS), \
             patch.object(pipeline, "generate_corpus_answer", return_value=AnswerResult("50%", ["E:b"])) as full, \
             patch.object(pipeline, "retrieve_memory", return_value=[]) as retrieve:
            pipeline.answer_question("Beacon?", "state-dir")
        return full.called, retrieve.called
    monkeypatch.setenv("CHRONICLE_FULL_CORPUS", "1")
    assert run() == (True, False)
    monkeypatch.delenv("CHRONICLE_FULL_CORPUS")
    assert run() == (False, True)
