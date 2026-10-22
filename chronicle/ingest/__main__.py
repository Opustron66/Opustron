"""CLI: ``python -m chronicle.ingest --corpus DIR --state DIR [--part a|b] [--model ID]``."""

import argparse
import os
import sys
from pathlib import Path

from chronicle.guard import LLMClient

from .consolidate import consolidate
from .pipeline import ingest_corpus

# Nemotron reasoning models spend thousands of tokens thinking before the JSON answer.
INGEST_MAX_TOKENS = 8192
# Off: with thinking on, Nemotron Lightning spends the whole budget reasoning on long docs
# and the JSON never arrives (corpus B run 1). Extraction is a reading task; it doesn't need it.
INGEST_THINKING = False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chronicle.ingest")
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--part", default=None, help="informational: which benchmark half is being ingested")
    p.add_argument("--model", default=None)
    p.add_argument("--workers", type=int, default=6, help="parallel extraction calls")
    p.add_argument("--timeout", type=float, default=180, help="per-call LLM timeout, seconds")
    p.add_argument("--max-tokens", type=int, default=INGEST_MAX_TOKENS, help="per-call completion budget")
    p.add_argument("--consolidate", action=argparse.BooleanOptionalAction,
                   default=os.environ.get("CHRONICLE_CONSOLIDATE", "1").lower() not in ("0", "false", "no", "off"),
                   help="build topic timelines and entity pages after ingesting (default: on)")
    p.add_argument("--thinking", action=argparse.BooleanOptionalAction, default=INGEST_THINKING,
                   help="let a reasoning model think before extracting (default: off)")
    args = p.parse_args(argv)
    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return 2
    # Privacy-routed: corpus text is pseudonymised before it leaves the machine and
    # every call is written to ~/.chronicle/egress.log.
    llm = LLMClient(default_model=args.model, timeout=args.timeout, max_tokens=args.max_tokens,
                    thinking=args.thinking)
    stats = ingest_corpus(args.corpus, args.state, llm, model=llm.model, workers=args.workers)
    print(f"[chronicle] part={args.part} {stats}", file=sys.stderr)
    if args.consolidate and stats.documents + stats.skipped:
        # CHRONICLE_CONSOLIDATE_MODEL: a stronger model for this one-time pass (default: same model).
        consolidator = llm
        if (other := os.environ.get("CHRONICLE_CONSOLIDATE_MODEL")) and other != llm.model:
            consolidator = LLMClient(default_model=other, timeout=args.timeout, max_tokens=args.max_tokens,
                                     thinking=args.thinking)
        pages = consolidate(args.state, consolidator, model=consolidator.model, workers=args.workers)
        print(f"[chronicle] consolidate {pages}", file=sys.stderr)
    return 1 if stats.failed and not stats.documents else 0


if __name__ == "__main__":
    raise SystemExit(main())
