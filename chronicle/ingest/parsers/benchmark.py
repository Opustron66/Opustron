"""NVIDIA benchmark input parser."""

import json
from collections.abc import Iterator
from pathlib import Path

from chronicle.schema import Document, Event, Source

from .markdown import parse_document


def parse(record: dict, *, uri: str = "memory://benchmark") -> Event:
    """Parse a benchmark record while retaining its original fields."""
    return Event(
        content=str(record.get("text", record.get("question", ""))),
        source=Source(uri=uri, kind="benchmark"),
        metadata=dict(record),
    )


def part_dirs(corpus: Path) -> list[tuple[str, Path]]:
    """Return ``[(part_name, dir)]`` with ``part_a`` before ``part_b``.

    ``corpus`` may be a single part directory (the adapter passes ``{corpus}`` per half),
    a ``corpus/`` directory containing ``part_*`` children, or a plain directory of documents.
    """
    children = sorted(p for p in corpus.iterdir() if p.is_dir() and p.name.startswith("part_"))
    if children:
        return [(p.name.removeprefix("part_"), p) for p in children]
    name = corpus.name.removeprefix("part_") if corpus.name.startswith("part_") else None
    return [(name, corpus)]  # type: ignore[list-item]
