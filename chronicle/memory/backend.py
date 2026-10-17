"""The Hermes memory backend, backed by the SQLite store.

Implements the ``ChronicleBackend`` protocol in ``chronicle.integrations.hermes_provider`` so P4
can pass ``SQLiteBackend()`` to ``ChronicleMemoryProvider`` (or ``SQLiteBackend(":memory:")`` in
tests) and memory survives Hermes restarts. Hermes memories are
free-text notes; ``recall`` searches notes and document claims alike, so a Hermes session over an
ingested corpus can recall both.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

from .api import MemoryAPI
from .database import MemoryDatabase
from .models import Fact

DEFAULT_DB = Path.home() / ".chronicle" / "memory.sqlite3"


def default_db_path() -> Path:
    """``$CHRONICLE_MEMORY_DB``, else ``~/.chronicle/memory.sqlite3``."""
    return Path(os.environ.get("CHRONICLE_MEMORY_DB") or DEFAULT_DB)


def _now() -> datetime:
    return datetime.now(UTC)


class SQLiteBackend:
    def __init__(self, api: MemoryAPI | MemoryDatabase | str | Path | None = None) -> None:
        if api is None:
            api = default_db_path()
        self.api = api if isinstance(api, MemoryAPI) else MemoryAPI(api)

    def remember(self, content, *, source, occurred_at=None, supersedes=None):
        return self.api.remember_note(content, source=source, at=occurred_at or _now(), supersedes=supersedes)

    def retire(self, content, *, at):
        self.api.retire_note(content, at=at)

    def recall(self, query, *, as_of=None, limit=5):
        from chronicle.integrations.hermes_provider import Recollection

        hits = self.api.search(query, as_of=as_of or _now(), k=limit)
        return [
            Recollection(h.fact.fact_id, h.fact.content, _source(h.fact), _instant(h.fact.valid_from),
                         _instant(h.fact.valid_to))
            for h in hits
        ]

    def close(self) -> None:
        self.api.close()


def _source(fact: Fact) -> str:
    source = fact.primary_source
    if source is None:
        return ""
    return source.uri or source.doc_id


def _instant(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime(value.year, value.month, value.day, tzinfo=UTC)
