from unittest.mock import patch

import pytest

from chronicle.reason.answerer import ANSWER_SCHEMA, generate_answer
from chronicle.reason.models import AnswerResult, Evidence, QueryPlan


def test_answer_calls_guard_with_json_schema_and_limits_citations():
    evidence = [Evidence("E:one", "Alice owns payments.", "2026-04-01")]
    with patch("chronicle.reason.answerer.llm.complete", return_value={
        "answer": "Alice", "source_ids": ["E:one", "E:invented", "E:one", 7],
    }) as complete:
        assert generate_answer(QueryPlan("Who owns payments?"), evidence) == AnswerResult("Alice", ["E:one"])
    messages = complete.call_args.args[0]
    assert "Who owns payments?" in messages[1]["content"]
    assert "Alice owns payments." in messages[1]["content"]
    assert complete.call_args.kwargs == {"schema": ANSWER_SCHEMA}


def test_no_evidence_abstains_without_calling_model():
    with patch("chronicle.reason.answerer.llm.complete") as complete:
        assert generate_answer(QueryPlan("unknown"), []) == AnswerResult("Not in the corpus", [])
    complete.assert_not_called()


def test_invalid_model_object_fails_explicitly():
    with patch("chronicle.reason.answerer.llm.complete", return_value=[]):
        with pytest.raises(ValueError, match="no JSON object"):
            generate_answer(QueryPlan("payments"), [Evidence("E:one", "payments")])


def test_agentic_loop_stops_after_three_rounds_and_must_answer():
    from chronicle.reason.answerer import AGENT_SCHEMA, MAX_ROUNDS, Tools
    searched = []
    tools = Tools(search=lambda qs: searched.append(qs) or [Evidence(f"E:{len(searched)}", "more", "2026-04-02")],
                  open=lambda ids: [])
    replies = [{"action": "search", "queries": ["payments owner"]}] * MAX_ROUNDS
    replies[-1] = {"action": "search", "queries": ["again"], "answer": "Alice", "source_ids": ["E:2"]}
    with patch("chronicle.reason.answerer.llm.complete", side_effect=replies) as complete:
        result = generate_answer(QueryPlan("Who owns payments?"), [Evidence("E:one", "payments")], tools)
    assert complete.call_count == MAX_ROUNDS == 3 and len(searched) == 2
    assert result == AnswerResult("Alice", ["E:2"])
    last = complete.call_args.args[0][1]["content"]
    assert "last turn" in last and "more" in last
    assert complete.call_args.kwargs == {"schema": AGENT_SCHEMA}


def test_agentic_loop_answers_in_one_round_when_it_can():
    from chronicle.reason.answerer import Tools
    tools = Tools(search=lambda qs: pytest.fail("no search needed"), open=lambda ids: [])
    with patch("chronicle.reason.answerer.llm.complete",
               return_value={"action": "answer", "answer": "Alice", "source_ids": ["E:one"]}) as complete:
        assert generate_answer(QueryPlan("x"), [Evidence("E:one", "Alice")], tools).answer == "Alice"
    assert complete.call_count == 1


def test_chain_questions_get_the_in_between_template():
    from chronicle.reason.answerer import answer_template
    assert "In between:" in answer_template(QueryPlan("The pour window moved more than once. Give the value it held in between, and the value now."))
    assert "earliest first" in answer_template(QueryPlan("Put these in the order they happened, earliest first: a; b"))
    assert answer_template(QueryPlan("Who owns payments?")) == ""
