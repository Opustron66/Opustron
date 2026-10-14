from datetime import date
import pytest
from chronicle.reason.models import Evidence
from chronicle.reason.pipeline import answer_question
from chronicle.reason.retriever import MockMemoryReader

@pytest.mark.parametrize(("question", "expected"), [
    ("Who managed payments on 2026-04-20?", "Alice"),
    ("Who managed payments on 2026-05-03?", "Bob"),
    ("Who manages payments?", "Bob"),
    ("Who managed payments on 2026-01-01?", "Not enough information"),
    ("What is Alice's salary?", "Not enough information"),
])
def test_pipeline(question, expected):
    result = answer_question(question, today=date(2026, 6, 1))
    assert result["answer"] == expected
    assert result["citations"] if expected != "Not enough information" else result["citations"] == []

def test_conflicting_facts_abstain():
    memory = MockMemoryReader()
    memory.facts.append(Evidence("payments", "manager", "Charlie", date(2026, 5, 1), None, "email_003", "Charlie manages payments."))
    assert answer_question("Who manages payments?", memory, today=date(2026, 6, 1))["answer"] == "Not enough information"

def test_invalid_date_raises():
    with pytest.raises(ValueError):
        answer_question("Who managed payments on 2026-99-99?")
