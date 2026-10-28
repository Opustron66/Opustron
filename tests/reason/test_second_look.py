from unittest.mock import MagicMock, patch

import pytest

from chronicle.reason import pipeline
from chronicle.reason.models import AnswerResult, Evidence


@pytest.mark.parametrize("answer,expected", [
    ("The corpus does not record who leads Project Beacon.", True),
    ("Not in the corpus", True),
    ("Rohan Dasgupta. He leads Beacon.", False),
    ("No. It was still in beta; the corpus does not record a launch.", False),
])
def test_gave_up_reads_only_the_first_sentence(answer, expected):
    assert pipeline.gave_up(answer) is expected


def _run(first, retry, monkeypatch, second_look="1"):
    monkeypatch.setenv("CHRONICLE_SECOND_LOOK", second_look)
    calls = []
    def retrieve(plan, memory, top_k=25, state=None, **wide):
        calls.append(wide)
        return [Evidence("E:one", "text", "2026-05-01")]
    with patch.object(pipeline, "open_state", return_value=MagicMock()), \
         patch.object(pipeline, "understand", side_effect=lambda plan: plan), \
         patch.object(pipeline, "retrieve_memory", side_effect=retrieve), \
         patch.object(pipeline, "generate_answer", side_effect=[first, retry]) as answer:
        result = pipeline.answer_question("Who leads Beacon?", "state-dir")
    return result, calls, answer


def test_second_look_replaces_a_give_up_that_it_can_answer_with_a_citation(monkeypatch):
    result, calls, answer = _run(AnswerResult("The corpus does not record it.", []),
                                 AnswerResult("Rohan Dasgupta.", ["E:one"]), monkeypatch)
    assert result == AnswerResult("Rohan Dasgupta.", ["E:one"])
    assert calls[1]["budget"] == pipeline.WIDE["budget"] > 40_000
    assert answer.call_args.args[3] == pipeline.SECOND_LOOK


@pytest.mark.parametrize("retry", [AnswerResult("Rohan Dasgupta.", []),
                                   AnswerResult("The corpus does not record it.", ["E:one"])])
def test_second_look_keeps_not_recorded_unless_the_retry_answers_and_cites(retry, monkeypatch):
    first = AnswerResult("The corpus does not record it.", [])
    assert _run(first, retry, monkeypatch)[0] == first


def test_no_second_look_for_answers_or_when_switched_off(monkeypatch):
    answered = AnswerResult("Rohan Dasgupta.", ["E:one"])
    result, calls, _ = _run(answered, None, monkeypatch)
    assert result == answered and len(calls) == 1
    gave_up = AnswerResult("Not in the corpus", [])
    result, calls, _ = _run(gave_up, None, monkeypatch, second_look="off")
    assert result == gave_up and len(calls) == 1
