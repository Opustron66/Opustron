from unittest.mock import patch

import pytest

from chronicle.reason import pipeline
from chronicle.reason.models import AnswerResult, QueryPlan


@pytest.mark.parametrize("question,answer,fires", [
    ("What sharing status does the primitive need?", "NOT shared (duplicated)", True),
    ("Of !312, !318 and !342, which is not real?", "!342 does not exist as a real merge request.", True),
    ("What sharing status does the primitive need?", "Duplicated. It is not shared.", False),
    ("Is prefix-trim on by default? Answer yes or no.", "No, it is not on by default.", False),
    ("Is Compass v1 the same as v2?", "They are not the same system.", False),
    ("Who leads Project Phoenix?", "The corpus does not record Project Phoenix.", False),
    ("How did the launch go?", "It has not launched yet.", False),
])
def test_needs_positive_form_only_for_negated_values(question, answer, fires):
    assert pipeline.needs_positive_form(QueryPlan(question), answer) is fires


def _rewrite(reply):
    with patch.object(pipeline.llm, "complete", return_value=reply) as complete:
        out = pipeline.positive_form(QueryPlan("What sharing status does it need?"),
                                     AnswerResult("NOT shared (duplicated)", ["E:1"]))
    return out, complete


def test_rewrite_keeps_citations_and_puts_the_value_first():
    out, complete = _rewrite({"answer": "Duplicated. It is not shared between Atlas and Beacon."})
    assert out == AnswerResult("Duplicated. It is not shared between Atlas and Beacon.", ["E:1"])
    assert "QUESTION: What sharing status" in complete.call_args.args[0][1]["content"]


@pytest.mark.parametrize("reply", [{"answer": "Not shared."}, {"answer": ""}, "junk",
                                   {"answer": "The corpus does not record it."}, {"answer": "x" * 400}])
def test_rejected_rewrites_keep_the_original(reply):
    assert _rewrite(reply)[0] == AnswerResult("NOT shared (duplicated)", ["E:1"])


def test_failed_rewrite_call_keeps_the_original():
    with patch.object(pipeline.llm, "complete", side_effect=ValueError("boom")):
        out = pipeline.positive_form(QueryPlan("What status?"), AnswerResult("NOT shared (duplicated)", []))
    assert out.answer == "NOT shared (duplicated)"


def test_answers_that_need_no_rewrite_make_no_call():
    with patch.object(pipeline.llm, "complete") as complete:
        assert pipeline.positive_form(QueryPlan("What status?"), AnswerResult("Duplicated.", [])).answer == "Duplicated."
    complete.assert_not_called()
