"""CLI: ``python -m chronicle.memory {serve,sync} --state DIR``."""

import argparse
import sys
from pathlib import Path

from .api import MemoryAPI


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="chronicle.memory")
    sub = p.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="load state/claims.jsonl into state/memory.sqlite3")
    sync.add_argument("--state", type=Path, required=True)
    serve = sub.add_parser("serve", help="serve the memory HTTP API for the UI")
    serve.add_argument("--state", type=Path, required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)

    if args.command == "sync":
        with MemoryAPI.from_state(args.state) as api:
            print(f"[chronicle.memory] {api.database.path}: {len(api.facts())} facts", file=sys.stderr)
        return 0

    import uvicorn

    from .server import create_app

    uvicorn.run(create_app(args.state), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
