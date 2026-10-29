from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from chronicle.reason import pipeline
from chronicle.reason.models import AnswerResult, Evidence, QueryPlan


@pytest.mark.parametrize("question,hard", [
    ("Is prefix-trim enabled by default? Answer yes or no.", True),
    ("Of Atlas, Beacon, Compass and Phoenix, which is not a real project?", True),
    ("How many security reviews are scheduled?", True),
    ("What MR did MR !521 do? Give both numbers.", True),
    ("What is the GitLab project path for Atlas?", False),
    ("Who owns payments?", False),
])
def test_hard_questions_are_the_flip_prone_shapes(question, hard):
    assert pipeline.is_hard(QueryPlan(question)) is hard


def test_as_of_questions_are_hard():
    assert pipeline.is_hard(QueryPlan("Who owned billing?", kind="as_of", reference_date=date(2026, 6, 9)))


@pytest.mark.parametrize("a,b,same", [
    ("No. It is defaulted off.", "no — it is opt-in per workspace", True),
    ("Phoenix.", "Phoenix. It has no documents.", True),
    ("Phoenix.", "Compass.", False),
    ("Yes.", "No.", False),
])
def test_vote_key_compares_polarity_or_first_sentence(a, b, same):
    assert (pipeline.vote_key(a) == pipeline.vote_key(b)) is same


def _samples(*answers):
    replies = iter(AnswerResult(a, []) for a in answers)
    temps = []
    def again(t):
        temps.append(t)
        return next(replies)
    return again, temps


def test_agreeing_second_sample_keeps_the_first_answer_without_a_third_call():
    again, temps = _samples("Yes, they are the same.")
    assert pipeline.vote(AnswerResult("Yes.", ["E:1"]), again) == AnswerResult("Yes.", ["E:1"])
    assert temps == [pipeline.VOTE_TEMPERATURE]


def test_two_later_samples_outvote_the_first():
    again, temps = _samples("No.", "No, distinct endpoints.")
    assert pipeline.vote(AnswerResult("Yes.", []), again).answer == "No."
    assert len(temps) == 2


def test_no_majority_keeps_the_first_answer():
    again, _ = _samples("Compass.", "Beacon.")
    assert pipeline.vote(AnswerResult("Phoenix.", []), again).answer == "Phoenix."


def test_pipeline_votes_only_on_hard_questions_when_enabled(monkeypatch):
    def run(question):
        with patch.object(pipeline, "open_state", return_value=MagicMock()), \
             patch.object(pipeline, "understand", side_effect=lambda plan: plan), \
             patch.object(pipeline, "retrieve_memory", return_value=[Evidence("E:1", "x", "2026-05-01")]), \
             patch.object(pipeline, "generate_answer", return_value=AnswerResult("Yes.", ["E:1"])) as answer:
            pipeline.answer_question(question, "state-dir")
        return answer.call_count
    hard = "Is prefix-trim on by default? Answer yes or no."
    assert run(hard) == 1  # off by default
    monkeypatch.setenv("CHRONICLE_VOTE", "1")
    assert run(hard) == 2 and run("Who owns payments?") == 1


@pytest.mark.parametrize("a,b,same", [
    ("Rohan Dasgupta.", "Rohan Dasgupta leads Beacon.", True),
    ("From 71% to 94%.", "MR !521 raised it from 71% to 94%.", True),
    ("Rohan Dasgupta.", "Anya Volkov.", False),
    ("The corpus does not record it.", "The corpus does not record who leads it.", True),
    ("The corpus does not record it.", "Rohan Dasgupta.", False),
    ("Yes. Both are reserved.", "No. Both are reserved.", False),
])
def test_samples_agree_when_they_make_the_same_claims(a, b, same):
    assert pipeline.agree(a, b, "Who leads Project Beacon?") is same


def test_with_no_two_agreeing_the_most_typical_answer_stays():
    # The third shares a claim with each of the others; the first and second share nothing.
    again, _ = _samples("Morgan Lee and Alex Chen.", "Rohan Dasgupta and Morgan Lee.")
    first = AnswerResult("Rohan Dasgupta and Jin Oh.", [])
    assert pipeline.vote(first, again, "Who proposed it and who shipped it?").answer == "Rohan Dasgupta and Morgan Lee."
