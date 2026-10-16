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
    p.add_argument("--workers", type=int, default=6, help="parallel extraction calls")
    p.add_argument("--timeout", type=float, default=180, help="per-call LLM timeout, seconds")
    args = p.parse_args(argv)
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2
    llm = OpenAICompatLLM(model=args.model, timeout=args.timeout)
    stats = ingest_corpus(args.corpus, args.state, llm, model=llm.model, workers=args.workers)
    print(f"[chronicle] part={args.part} {stats}", file=sys.stderr)
    print(f"[chronicle] llm calls={llm.calls} prompt_tokens={llm.prompt_tokens} completion_tokens={llm.completion_tokens}", file=sys.stderr)
    return 1 if stats.failed and not stats.documents else 0


if __name__ == "__main__":
    raise SystemExit(main())
