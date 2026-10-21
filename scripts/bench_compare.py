"""Compare benchmark runs: per-type accuracy side by side, and per-question flips.

    python scripts/bench_compare.py RUN_DIR [RUN_DIR ...] [--questions questions.jsonl] [--flips]

Each RUN_DIR is a ``bench.runner`` output directory holding ``report.json`` and
``verdicts.jsonl``. Only the verdicts' ``correct`` flags are read; never the grader's
reasons or the gold answers. ``--flips`` lists questions whose result changed between
consecutive runs (needs ``--questions`` to show each question's type).
"""

import argparse
import json
from pathlib import Path


def load_report(run: Path) -> dict:
    return json.loads((run / "report.json").read_text())["summary"]


def load_correct(run: Path) -> dict[str, bool]:
    out = {}
    for line in (run / "verdicts.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["question_id"]] = bool(row["correct"])
    return out


def load_types(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    return {q["id"]: q.get("type", "?") for q in map(json.loads, path.read_text().splitlines()) if q}


def table(runs: list[Path], names: list[str]) -> str:
    summaries = [load_report(r) for r in runs]
    types = sorted({t for s in summaries for t in s["accuracy_by_type"]})
    width = max(len(n) for n in names + ["overall"]) + 2
    lines = ["type".ljust(18) + "".join(n.rjust(width) for n in names)]
    for t in types:
        cells = [s["accuracy_by_type"].get(t) for s in summaries]
        lines.append(t.ljust(18) + "".join(("-" if c is None else f"{c:.3f}").rjust(width) for c in cells))
    lines.append("overall".ljust(18) + "".join(f"{s['accuracy_overall']:.3f}".rjust(width) for s in summaries))
    lines.append("questions".ljust(18) + "".join(str(s["questions"]).rjust(width) for s in summaries))
    return "\n".join(lines)


def flips(before: Path, after: Path, types: dict[str, str]) -> str:
    a, b = load_correct(before), load_correct(after)
    gained = sorted(q for q in a.keys() & b.keys() if b[q] and not a[q])
    lost = sorted(q for q in a.keys() & b.keys() if a[q] and not b[q])
    lines = [f"{before.name} -> {after.name}: +{len(gained)} -{len(lost)}"]
    lines += [f"  + [{types.get(q, '?')}] {q}" for q in gained]
    lines += [f"  - [{types.get(q, '?')}] {q}" for q in lost]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="bench_compare")
    p.add_argument("runs", nargs="+", type=Path)
    p.add_argument("--names", nargs="*", help="column labels (default: run directory names)")
    p.add_argument("--questions", type=Path, help="questions.jsonl, for question types in --flips")
    p.add_argument("--flips", action="store_true", help="list per-question changes between consecutive runs")
    args = p.parse_args(argv)
    names = args.names or [r.name for r in args.runs]
    if len(names) != len(args.runs):
        p.error("--names needs one label per run")
    print(table(args.runs, names))
    if args.flips:
        types = load_types(args.questions)
        for before, after in zip(args.runs, args.runs[1:]):
            print()
            print(flips(before, after, types))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
