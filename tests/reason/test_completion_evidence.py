import sys
from datetime import date
from types import ModuleType
from unittest.mock import patch

import pytest

from chronicle.reason.answerer import (
    ANSWER_FORM,
    EVIDENCE_RULES,
    FALLBACK_CONTRACT,
    GROUNDING,
    generate_answer,
)
from chronicle.reason.models import Evidence, QueryPlan


@pytest.mark.parametrize(("evidence", "answer"), [
    ("The demo is scheduled for 2026-06-30.", "The corpus does not confirm whether the demo happened."),
    ("The demo was completed on 2026-06-19.", "Yes, completed on 2026-06-19."),
    ("As of 2026-06-20, the demo has explicitly not been completed.", "No, not completed as of 2026-06-20."),
])
def test_evidence_and_status_rules_reach_guard_without_overwriting_model_status(evidence, answer):
    # Status remains grounded in the model's evidence reading, not a blanket yes/no rewrite.
    with patch("chronicle.reason.answerer.llm.complete", return_value={"answer": answer, "source_ids": ["demo"]}) as complete:
        result = generate_answer(QueryPlan("Has the demo happened?", "as_of", date(2026, 6, 20)),
                                 [Evidence("demo", evidence)])
    messages = complete.call_args.args[0]
    assert EVIDENCE_RULES in messages[0]["content"]
    assert evidence in messages[1]["content"]
    assert "Answer as of 2026-06-20" in messages[1]["content"]
    assert result.answer == answer and result.source_ids == ["demo"]


def test_external_benchmark_contract_does_not_remove_evidence_rules(monkeypatch):
    bench = ModuleType("bench")
    contract = ModuleType("bench.answer_contract")
    contract.ANSWER_CONTRACT = "External benchmark formatting contract: return JSON."
    monkeypatch.setitem(sys.modules, "bench", bench)
    monkeypatch.setitem(sys.modules, "bench.answer_contract", contract)
    with patch("chronicle.reason.answerer.llm.complete", return_value={"answer": "Not confirmed", "source_ids": []}) as complete:
        generate_answer(QueryPlan("Was the demo completed?"), [Evidence("demo", "Demo scheduled June 30.")])
    system = complete.call_args.args[0][0]["content"]
    assert contract.ANSWER_CONTRACT in system
    assert EVIDENCE_RULES in system and ANSWER_FORM in system and system.endswith(GROUNDING)
    assert "Something only scheduled has not happened" not in FALLBACK_CONTRACT
