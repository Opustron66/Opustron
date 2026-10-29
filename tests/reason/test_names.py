import json

import pytest

from chronicle.reason import names, pipeline
from chronicle.reason.models import AnswerResult, Evidence


@pytest.fixture
def state(tmp_path):
    (tmp_path / "roster.json").write_text(json.dumps({"people": ["Sam Iverson", "Rohan Dasgupta", "ReviewBot"]}))
    docs = [{"text": "to:\n  - Jin Oh (@jin) <jin.oh@example.com>\ncc: Platform Eng Ops <eng-ops@example.com>"},
            {"text": "[ts] Alex Chen (U200AC3F7E12): Hello Alex, View Merge request"}]
    (tmp_path / "docs.jsonl").write_text("".join(json.dumps(d) + "\n" for d in docs))
    names._state_people.cache_clear()
    return tmp_path


def test_people_come_from_the_roster_and_from_senders_recipients_and_speakers(state):
    assert names.load_people(state) == ["Alex Chen", "Jin Oh", "Rohan Dasgupta", "Sam Iverson"]
    assert names.load_people(None) == []


@pytest.mark.parametrize("answer,expected", [
    ("Jin.", "Jin Oh."),
    ("30-40% of Jin's week.", "30-40% of Jin Oh's week."),
    ("Sam Iverson and Rohan.", "Sam Iverson and Rohan Dasgupta."),
    ("Rohan Dasgupta leads it; Rohan approved.", "Rohan Dasgupta leads it; Rohan approved."),
    ("Platform Eng owns it.", "Platform Eng owns it."),
    ("Hello there.", "Hello there."),
])
def test_lone_first_names_of_known_people_are_written_in_full(state, answer, expected):
    assert names.full_names(answer, names.load_people(state), []) == expected


def test_a_first_name_two_people_share_is_left_alone():
    assert names.full_names("Alex.", ["Alex Chen", "Alex Nova"], []) == "Alex."


def test_with_names_masked_the_evidence_is_written_in_full_before_answering(state, monkeypatch):
    monkeypatch.setenv("CHRONICLE_REDACT_NAMES", "1")
    seen = []

    class Memory:
        class database:
            path = str(state / "memory.sqlite3")

        def close(self):
            pass

    def fake_answer(plan, evidence, tools=None, hint="", temperature=0.0):
        seen.extend(e.text for e in evidence)
        seen.append(plan.question)
        return AnswerResult("Rohan.", ["S:1"])

    monkeypatch.setattr(pipeline, "MemoryAPI", Memory)
    monkeypatch.setattr(pipeline, "retrieve_memory", lambda *a, **k: [Evidence("S:1", "Rohan from Beacon; Rohan's team")])
    monkeypatch.setattr(pipeline, "generate_answer", fake_answer)
    monkeypatch.setattr(pipeline, "understand", lambda plan: plan)
    monkeypatch.setenv("CHRONICLE_AGENTIC", "0")
    monkeypatch.setenv("CHRONICLE_GROUNDING", "0")
    result = pipeline.answer_question("Does Rohan lead Project Beacon?", Memory())
    assert seen == ["Rohan Dasgupta from Beacon; Rohan Dasgupta's team", "Does Rohan Dasgupta lead Project Beacon?"]
    assert result.answer == "Rohan Dasgupta."
