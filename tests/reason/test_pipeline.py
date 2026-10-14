import io
import json
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch
from chronicle.reason.planner import plan_query
from chronicle.reason.retriever import retrieve
from chronicle.reason.models import AnswerResult
from adapters.chronicle.ingest import ingest_corpus
from adapters.chronicle.answer import run
from eval.metrics import summarize

def test_planner_as_of():
    p = plan_query("Who owned payments on 2026-05-03?")
    assert p.kind == "as_of" and p.reference_date == date(2026, 5, 3)

def test_planner_current():
    assert plan_query("Who currently owns payments?").kind == "current"

def test_ingest_twice_and_retrieve(tmp_path):
    a, b, state = tmp_path / "a", tmp_path / "b", tmp_path / "state"
    a.mkdir(); b.mkdir()
    (a / "one.md").write_text("---\ndoc_id: E:one\ndate: 2026-04-01\nsubject: payments\n---\nAlice managed payments.", encoding="utf-8")
    (b / "two.md").write_text("---\ndoc_id: E:two\ndate: 2026-05-01\nsubject: payments\n---\nBob replaced Alice in payments.", encoding="utf-8")
    ingest_corpus(a, state); ingest_corpus(b, state)
    with sqlite3.connect(state / "chronicle_adapter.sqlite3") as conn:
        assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == 2
    assert len(retrieve(plan_query("Who managed payments?"), state)) == 2

def test_answer_jsonl_shape(tmp_path):
    inp = io.StringIO('{"id":"q1","question":"unknown"}\n')
    out = io.StringIO()
    with patch("adapters.chronicle.answer.answer_question", return_value=AnswerResult("Bob", ["E:two"])):
        run(tmp_path, inp, out)
    assert json.loads(out.getvalue()) == {"id":"q1", "answer":"Bob", "source_ids":["E:two"]}

def test_summary():
    assert summarize([{"category":"as_of","correct":True},{"category":"as_of","correct":False}])["as_of"]["accuracy"] == .5
