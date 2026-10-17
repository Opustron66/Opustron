"""Application-facing memory API: the one object P3, P4 and the HTTP server talk to.

    from chronicle.memory.api import MemoryAPI

    memory = MemoryAPI.from_state(".tmp/chronicle")  # opens state/memory.sqlite3, loads claims.jsonl
    memory.holder_at("owns", "payments service", "2026-05-03")  # -> Fact(subject="Alice Chen", ...)
    memory.search("who owns payments", as_of="2026-05-20")
"""

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Self

from chronicle.schema import Claim, Event

from . import queries
from .database import MemoryDatabase
from .models import EntityRecord, Fact, IngestReport, SearchHit, TimelineEvent
from .search import search as search_facts

DB_FILE = "memory.sqlite3"
CLAIMS_FILE = "claims.jsonl"  # written by P1's chronicle.ingest

When = date | datetime | str


class MemoryAPI:
    def __init__(self, database: MemoryDatabase | str | Path | None = None) -> None:
        if database is None or isinstance(database, (str, Path)):
            database = MemoryDatabase(database or ":memory:")
        self.database = database
        self._events: dict[str, Event] = {}

    @classmethod
    def from_state(cls, state: str | Path, *, sync: bool = True) -> "MemoryAPI":
        """Open ``state/memory.sqlite3``. With ``sync``, first load any claims P1 has appended to
        ``state/claims.jsonl`` since the last open (already-stored claims are skipped)."""
        state = Path(state)
        api = cls(MemoryDatabase(state / DB_FILE))
        if sync:
            api.sync_claims_file(state / CLAIMS_FILE)
        return api

    def close(self) -> None:
        self.database.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- writes --------------------------------------------------------------------------------

    def ingest_claims(self, claims: Iterable[Claim], *, uri: str | None = None) -> IngestReport:
        """Store P1 claims. Idempotent: the same claim twice is counted as a duplicate."""
        report = IngestReport()
        for claim in claims:
            outcome, _, superseded = self.database.add_claim(claim, uri=uri)
            counter = "duplicates" if outcome == "duplicate" else outcome
            setattr(report, counter, getattr(report, counter) + 1)
            report.superseded += superseded
        return report

    def sync_claims_file(self, path: str | Path) -> IngestReport:
        path = Path(path)
        if not path.is_file():
            return IngestReport()
        with path.open(encoding="utf-8") as lines:
            return self.ingest_claims(Claim.model_validate_json(line) for line in lines if line.strip())

    def remember_note(self, content: str, *, source: str, at: datetime | None = None,
                      supersedes: str | None = None) -> str:
        """Store a free-text fact (Hermes). ``supersedes`` closes an earlier note, by id or content."""
        return self.database.add_note(content, source=source, at=at, supersedes=supersedes)

    def retire_note(self, content_or_id: str, *, at: datetime) -> int:
        """Mark a note as no longer true from ``at``. Returns how many notes were closed."""
        return self.database.retire_note(content_or_id, at=at)

    def add_alias(self, alias: str, name: str) -> None:
        self.database.add_alias(alias, name)

    def remember(self, event: Event) -> Event:
        """Legacy in-process event list, kept for ``hermes_provider.InMemoryBackend``.

        Events here are not persisted; new code should use ``remember_note`` or
        ``chronicle.memory.backend.SQLiteBackend``.
        """
        self._events[event.event_id] = event
        return event

    def list_memories(self) -> list[Event]:
        return list(self._events.values())

    # -- reads ---------------------------------------------------------------------------------

    def as_of(self, when: When, *, known_at: When | None = None, subject: str | None = None,
              predicate: str | None = None, object: str | None = None, kind: str | None = None) -> list[Fact]:
        return queries.as_of(self.database, when, known_at=known_at, subject=subject,
                             predicate=predicate, object=object, kind=kind)

    def current(self, **filters) -> list[Fact]:
        return self.as_of(datetime.now().astimezone(), **filters)

    def facts(self, **filters) -> list[Fact]:
        """Every fact, superseded ones included."""
        return queries.all_facts(self.database, **filters)

    def fact(self, fact_id: str, *, known_at: When | None = None) -> Fact | None:
        found = self.database.facts("fact_id = ?", [fact_id], known_at=known_at)
        return found[0] if found else None

    def versions(self, fact_id: str) -> list[Fact]:
        return self.database.versions(fact_id)

    def value_at(self, subject: str, predicate: str, when: When, **kw) -> Fact | None:
        return queries.value_at(self.database, subject, predicate, when, **kw)

    def holder_at(self, predicate: str, obj: str, when: When, **kw) -> Fact | None:
        return queries.holder_at(self.database, predicate, obj, when, **kw)

    def history(self, entity: str, *, known_at: When | None = None) -> list[Fact]:
        return queries.history(self.database, entity, known_at=known_at)

    def timeline(self, start: When, end: When, **kw) -> list[TimelineEvent]:
        return queries.timeline(self.database, start, end, **kw)

    def entities(self) -> list[EntityRecord]:
        return queries.entities(self.database)

    def entity(self, id_or_name: str) -> EntityRecord | None:
        return queries.find_entity(self.database, id_or_name)

    def span(self) -> tuple[date | None, date | None]:
        return queries.span(self.database)

    def search(self, query: str, *, as_of: When | None = None, known_at: When | None = None,
               k: int = 10, kind: str | None = None) -> list[SearchHit]:
        return search_facts(self.database, query, as_of=as_of, known_at=known_at, k=k, kind=kind)
