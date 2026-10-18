from datetime import date
from unittest.mock import patch

import pytest

from chronicle.memory import MemoryAPI
from chronicle.reason.pipeline import answer_question
from chronicle.reason.planner import lexical_query, plan_query
from chronicle.reason.retriever import retrieve
from chronicle.schema import Claim


@pytest.mark.parametrize("date_text", ["2026-05-31", "May 31", "31 May", "May 31st, 2026"])
def test_question_date_cannot_retrieve_unrelated_record_by_year(date_text):
    with MemoryAPI() as memory:
        memory.ingest_claims([
            Claim(subject="invoice export", predicate="deadline", object="deadline", valid_to="2026-06-18",
                  observed_at="2026-06-12", doc_id="unrelated", quote="Export moved from 2026-06-18 to 2026-06-25."),
            Claim(subject="Maya", predicate="owns", object="billing", valid_from="2026-06-01",
                  doc_id="billing", quote="Maya owns billing."),
        ])
        question = f"Who owned billing on {date_text}?"
        plan = plan_query(question, as_of=date(2026, 6, 20))
        assert plan.reference_date == date(2026, 5, 31)
        assert retrieve(plan, memory) == []
        with patch("chronicle.reason.answerer.llm.complete") as model:
            result = answer_question(question, memory, as_of=date(2026, 6, 20))
        assert result.answer == "Not in the corpus" and result.source_ids == []
        model.assert_not_called()


def test_date_filter_and_original_question_still_reach_answerer():
    with MemoryAPI() as memory:
        memory.ingest_claims([
            Claim(subject="Maya", predicate="owns", object="billing", valid_from="2026-06-01", doc_id="old", quote="Maya owns billing."),
            Claim(subject="Noah", predicate="owns", object="billing", valid_from="2026-06-10", doc_id="new", quote="Noah owns billing."),
        ])
        question = "Who owned billing on June 9?"
        with patch("chronicle.reason.answerer.llm.complete", return_value={"answer":"Maya", "source_ids":["old"]}) as model:
            answer_question(question, memory, as_of=date(2026, 6, 20))
        prompt = model.call_args.args[0][1]["content"]
        assert question in prompt and "Answer as of 2026-06-09" in prompt
        assert '"subject": "Maya"' in prompt and '"subject": "Noah"' not in prompt


def test_history_keeps_comparison_words_and_owners():
    question = "Who owned billing before June 10, 2026?"
    assert "before" in lexical_query(question) and "June" not in lexical_query(question)
    assert plan_query(question).reference_date is None
    with MemoryAPI() as memory:
        memory.ingest_claims([
            Claim(subject="Maya", predicate="owns", object="billing", valid_from="2026-06-01", doc_id="old", quote="Maya owns billing."),
            Claim(subject="Noah", predicate="owns", object="billing", valid_from="2026-06-10", doc_id="new", quote="Noah owns billing."),
        ])
        assert {e.doc_id for e in retrieve(plan_query(question), memory)} == {"old", "new"}


def test_numeric_entity_names_are_not_stripped_as_years():
    question = "Who owns Apollo 2026?"
    assert lexical_query(question) == question
    with MemoryAPI() as memory:
        memory.ingest_claims([Claim(subject="Maya", predicate="owns", object="Apollo 2026",
                                   doc_id="apollo", quote="Maya owns Apollo 2026.")])
        assert [e.doc_id for e in retrieve(plan_query(question), memory)] == ["apollo"]


def test_date_only_query_has_no_lexical_evidence():
    assert lexical_query("2026-06-09") == ""
