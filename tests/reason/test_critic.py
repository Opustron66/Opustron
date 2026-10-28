from unittest.mock import patch

import pytest

from chronicle.reason import critic, pipeline
from chronicle.reason.models import AnswerResult, Evidence, QueryPlan

EVIDENCE = [
    Evidence("S:1", "Alex Chen: talked to Morgan today about the meeting load thing. she's going to absorb "
                    "the customer council slot and we're collapsing the Beacon sync to biweekly.",
             "2026-05-13", kind="chunk"),
    Evidence("E:2", "Send it Mon morning, I'll read on my commute.", "2026-05-22", kind="chunk"),
]
PLAN = QueryPlan("What mitigations were put in place for Jordan's meeting load? Name them.")
DRAFT = AnswerResult("Morgan Lee took over the customer council slot.", ["S:1"])
FIX = {"verdict": "fix", "problem": "Misses the Beacon sync change.",
       "quote": "we're collapsing the Beacon sync to biweekly",
       "answer": "Morgan Lee took over the customer council slot, and the Beacon sync moved to biweekly.",
       "source_ids": ["S:1", "X:not-in-evidence"]}


def test_a_fix_proven_by_a_verbatim_quote_replaces_the_draft():
    fixed = critic.accept(PLAN, DRAFT, FIX, EVIDENCE)
    assert fixed == AnswerResult(FIX["answer"], ["S:1"])


@pytest.mark.parametrize("reply", [
    {"verdict": "ok"},
    {**FIX, "quote": "we moved the Beacon sync to monthly"},  # not in the evidence
    {**FIX, "quote": "biweekly"},  # too short to prove anything
    {**FIX, "answer": "  "},
    "not a dict",
])
def test_the_draft_stays_unless_the_fix_is_proven(reply):
    assert critic.accept(PLAN, DRAFT, reply, EVIDENCE) is DRAFT


def test_a_refusal_replaces_only_a_draft_the_grounding_check_flagged():
    refusal = {**FIX, "answer": "The corpus does not record any mitigation."}
    assert critic.accept(PLAN, DRAFT, refusal, EVIDENCE, pipeline.gave_up) is DRAFT
    flagged = AnswerResult("Ready to merge.", ["S:1"], unsupported=["ready"])
    assert critic.accept(PLAN, flagged, refusal, EVIDENCE, pipeline.gave_up).answer == refusal["answer"]


def test_critique_sends_question_draft_and_evidence_and_survives_errors():
    with patch("chronicle.reason.critic.llm.complete", return_value=FIX) as complete:
        assert critic.critique(PLAN, DRAFT, EVIDENCE).answer == FIX["answer"]
    user = complete.call_args.args[0][1]["content"]
    assert "DRAFT ANSWER: Morgan Lee took over" in user and "collapsing the Beacon sync" in user
    assert "Every part" in complete.call_args.args[0][0]["content"]
    with patch("chronicle.reason.critic.llm.complete", side_effect=RuntimeError("down")):
        assert critic.critique(PLAN, DRAFT, EVIDENCE) is DRAFT


def test_critic_is_off_by_default(monkeypatch):
    monkeypatch.delenv("CHRONICLE_CRITIC", raising=False)
    assert not critic.critic_enabled()
    monkeypatch.setenv("CHRONICLE_CRITIC", "1")
    assert critic.critic_enabled()


@pytest.mark.parametrize("answer,expected", [
    ("Provider C has experimental status and does not fully support it.",
     "Provider C has experimental status; it does not fully support it."),
    ("Duplicated, which is not shared.", "Duplicated; it is not shared."),
    ("Rohan Dasgupta proposed it and never shipped it.", "Rohan Dasgupta proposed it; it never shipped it."),
    ("Not shared yet.", "Not shared yet."),
    ("The corpus does not record it and does not say why.", "The corpus does not record it and does not say why."),
])
def test_a_negation_joined_with_and_becomes_its_own_clause(answer, expected):
    assert pipeline.split_negations(AnswerResult(answer, ["E:1"])).answer == expected
