"""NVIDIA mnemo answer adapter: JSONL stdin -> JSONL stdout."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Works when called from the benchmark root or the Chronicle repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from chronicle.reason.pipeline import answer_question

NOT_IN_CORPUS = "Not in the corpus"


def run(state: Path, instream=sys.stdin, outstream=sys.stdout):
    for line_number, line in enumerate(instream, start=1):
        if not line.strip():
            continue
        try:
            question = json.loads(line)
        except json.JSONDecodeError:
            print(f"[chronicle] skipping line {line_number}: invalid JSON", file=sys.stderr)
            continue
        if (not isinstance(question, dict)
                or not isinstance(question.get("id"), str)
                or not isinstance(question.get("question"), str)):
            print(
                f"[chronicle] skipping line {line_number}: expected an object with string 'id' and 'question'",
                file=sys.stderr,
            )
            continue
        as_of = question.get("as_of")
        if as_of is not None:
            try:
                as_of = date.fromisoformat(as_of)
            except (TypeError, ValueError):
                print(f"[chronicle] skipping line {line_number}: invalid 'as_of' date", file=sys.stderr)
                continue
        try:
            result = (answer_question(question["question"], state, as_of=as_of) if as_of is not None
                      else answer_question(question["question"], state))
            answer, source_ids = result.answer, result.source_ids
        except Exception as exc:  # noqa: BLE001 - one bad reply must not end the run
            print(f"[chronicle] {question['id']}: answering failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            answer, source_ids = NOT_IN_CORPUS, []
        print(json.dumps({"id": question["id"], "answer": answer, "source_ids": source_ids}), file=outstream, flush=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--state", type=Path, required=True)
    args = p.parse_args()
    run(args.state)

if __name__ == "__main__":
    main()
