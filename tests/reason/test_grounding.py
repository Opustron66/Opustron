from datetime import date
from unittest.mock import patch

import pytest

from chronicle.reason import pipeline
from chronicle.reason.answerer import (
    ANSWER_SCHEMA,
    TIMELINE_SCHEMA,
    _messages,
    generate_answer,
    needs_timeline,
)
from chronicle.reason.grounding import claims, unsupported
from chronicle.reason.models import AnswerResult, Evidence, QueryPlan

EVIDENCE = ["Rohan Dasgupta: worth porting to atlas?\nMorgan Lee: yes, worth it.",
            "cache hit rate on the smoke fixture goes from 71% to 94%.",
            "Ingest: lower default backfill window from 30d to 14d on cold start"]


@pytest.mark.parametrize("answer,question,expected", [
    ("Morgan Lee proposed it; Alex Chen shipped it.", "Who proposed porting it?", ["Morgan Lee", "Alex Chen"]),
    ("From 71% to 94%.", "What did MR !521 do? Give both numbers.", ["71%", "94%"]),
    ("ready to merge", "Has merge request !342 been opened and reviewed?", ["ready"]),
    ("Phoenix.", "Of Atlas, Beacon, Compass and Phoenix, which is not real?", []),
    ("No. As of 2026-05-10 it was below 50%.", "Had Beacon reached its 50% cohort?", []),
])
def test_claims_are_names_numbers_and_short_values_not_in_the_question(answer, question, expected):
    assert claims(answer, question) == expected


def test_only_quotes_that_really_occur_in_the_evidence_back_a_claim():
    q = "What did MR !521 do to the hit rate? Give both numbers."
    assert unsupported("From 71% to 94%.", [{"quote": "goes from 71% to 94%"}], q, EVIDENCE) == []
    invented = [{"quote": "the hit rate went from 71% to 94% overnight"}]
    assert unsupported("From 71% to 94%.", invented, q, EVIDENCE) == ["71%", "94%"]
    assert unsupported("99.2% on the smoke test.", [{"quote": "goes from 71% to 94%"}], q, EVIDENCE)


def test_units_and_refusals_need_no_quote():
    q = "As of 2026-05-20, what was the default backfill window?"
    assert unsupported("30 days.", [{"quote": "lower default backfill window from 30d to 14d"}], q, EVIDENCE) == []
    assert unsupported("The corpus does not record it.", [], q, EVIDENCE) == []


def test_generate_answer_reports_unsupported_claims():
    reply = {"answer": "Morgan Lee proposed it.", "source_ids": ["E:1"], "support": [{"quote": "Morgan Lee: yes, worth it."}]}
    with patch("chronicle.reason.answerer.llm.complete", return_value=reply):
        result = generate_answer(QueryPlan("Who proposed porting top-K?"), [Evidence("E:1", EVIDENCE[0], "2026-05-15")])
    assert result == AnswerResult("Morgan Lee proposed it.", ["E:1"]) and result.unsupported == []
    reply = {"answer": "Felix Oduya proposed it.", "source_ids": ["E:1"]}
    with patch("chronicle.reason.answerer.llm.complete", return_value=reply):
        result = generate_answer(QueryPlan("Who proposed porting top-K?"), [Evidence("E:1", EVIDENCE[0], "2026-05-15")])
    assert "Felix Oduya" in result.unsupported


def test_recheck_asks_once_and_keeps_the_better_backed_answer():
    bad = AnswerResult("Felix Oduya.", [], unsupported=["Felix Oduya"])
    hints = []
    good = AnswerResult("Rohan Dasgupta.", ["E:1"])
    assert pipeline.recheck(QueryPlan("Who?"), bad, lambda h: hints.append(h) or good) == good
    assert "Felix Oduya" in hints[0] and len(hints) == 1
    worse = AnswerResult("Sam and Felix.", [], unsupported=["Sam", "Felix"])
    assert pipeline.recheck(QueryPlan("Who?"), bad, lambda h: worse) == bad


def test_backed_answers_and_refusals_are_not_rechecked():
    called = []
    ok = AnswerResult("Rohan Dasgupta.", ["E:1"])
    assert pipeline.recheck(QueryPlan("Who?"), ok, lambda h: called.append(h)) == ok
    refusal = AnswerResult("The corpus does not record it.", [], unsupported=["x"])
    assert pipeline.recheck(QueryPlan("Who?"), refusal, lambda h: called.append(h)) == refusal
    assert called == []


@pytest.mark.parametrize("plan,expected", [
    (QueryPlan("Describe how Beacon's state changed over the corpus window: where it started and where it ended."), True),
    (QueryPlan("Is Jordan's meeting load still unaddressed, or have mitigations been put in place?"), True),
    (QueryPlan("Who owned billing?", kind="as_of", reference_date=date(2026, 6, 9)), True),
    (QueryPlan("What is the GitLab project path for Atlas?"), False),
])
def test_state_over_time_questions_get_the_timeline(plan, expected):
    assert needs_timeline(plan) is expected
    system = _messages(plan, [Evidence("E:1", "x")], agentic=False, last=True)[0]["content"]
    assert ("Timeline first" in system) is expected


def test_timeline_questions_use_the_timeline_schema_with_timeline_before_answer():
    assert list(TIMELINE_SCHEMA["properties"])[:2] == ["timeline", "answer"]
    plan = QueryPlan("Describe how Beacon's state changed over the corpus window.")
    with patch("chronicle.reason.answerer.llm.complete", return_value={"answer": "x", "source_ids": []}) as complete:
        generate_answer(plan, [Evidence("E:1", "x")])
    assert complete.call_args.kwargs["schema"] == TIMELINE_SCHEMA
    with patch("chronicle.reason.answerer.llm.complete", return_value={"answer": "x", "source_ids": []}) as complete:
        generate_answer(QueryPlan("Who owns payments?"), [Evidence("E:1", "x")])
    assert complete.call_args.kwargs["schema"] == ANSWER_SCHEMA
