"""CLI: ``python -m chronicle.ingest --corpus DIR --state DIR [--part a|b] [--model ID]``."""

import argparse
import sys
from pathlib import Path

from .llm import OpenAICompatLLM
from .pipeline import ingest_corpus


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chronicle.ingest")
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--part", default=None, help="informational: which benchmark half is being ingested")
    p.add_argument("--model", default=None)
    args = p.parse_args(argv)
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2
    llm = OpenAICompatLLM(model=args.model)
    stats = ingest_corpus(args.corpus, args.state, llm, model=llm.model)
    print(f"[chronicle] part={args.part} {stats}", file=sys.stderr)
    return 1 if stats.failed and not stats.documents else 0


if __name__ == "__main__":
    raise SystemExit(main())
