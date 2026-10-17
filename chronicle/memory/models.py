"""Memory-layer models and the time helpers the store uses.

All instants are stored as fixed-width UTC ISO strings (``to_ts``), so SQLite text comparison
orders them. Day-granularity facts (everything P1 extracts) are stored at midnight UTC and come
back out as ``date``s; Hermes notes are stored to the microsecond and come back as ``datetime``s.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from typing import Any

from chronicle.schema import Claim, Entity, Event, Source

__all__ = [
    "Claim", "Entity", "EntityRecord", "Event", "Fact", "FactSource", "IngestReport",
    "SearchHit", "Source", "TimelineEvent", "from_ts", "parse_when", "to_ts",
]

_TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%f+00:00"


def to_ts(value: date | datetime | str | None, *, end_of_day: bool = False) -> str | None:
    """Normalise a date, datetime or ISO string to the store's UTC text format.

    A bare date means midnight, or the last microsecond of the day with ``end_of_day``.
    Naive datetimes are taken as UTC.
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = parse_when(value)
    if not isinstance(value, datetime):
        value = datetime.combine(value, time.max if end_of_day else time.min)
    value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return value.strftime(_TS_FORMAT)


def from_ts(value: str | None, granularity: str = "instant") -> date | datetime | None:
    if value is None:
        return None
    moment = datetime.strptime(value, _TS_FORMAT).replace(tzinfo=UTC)
    return moment.date() if granularity == "day" else moment


def parse_when(value: str) -> date | datetime:
    """``YYYY-MM-DD`` becomes a date; anything longer must be an ISO datetime."""
    value = value.strip()
    if len(value) == 10:
        return date.fromisoformat(value)
    return datetime.fromisoformat(value)


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


@dataclass(slots=True)
class FactSource:
    """One document statement behind a fact."""

    doc_id: str
    quote: str
    role: str  # opened | restated | closed
    observed_at: date | datetime | None = None
    valid_from: date | datetime | None = None
    valid_to: date | datetime | None = None
    confidence: float = 1.0
    uri: str | None = None
    recorded_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id, "quote": self.quote, "role": self.role,
            "observed_at": _iso(self.observed_at), "valid_from": _iso(self.valid_from),
            "valid_to": _iso(self.valid_to), "confidence": self.confidence, "uri": self.uri,
        }


@dataclass(slots=True)
class Fact:
    """One version of a fact: what it says, when it was true, and when Chronicle knew it.

    ``valid_from``/``valid_to`` are half-open: the fact holds on ``valid_from`` and no longer
    holds on ``valid_to``. ``None`` means unknown start or still true.
    """

    fact_id: str
    kind: str
    subject: str
    predicate: str
    object: str
    content: str
    valid_from: date | datetime | None
    valid_to: date | datetime | None
    granularity: str
    recorded_at: datetime
    replaced_at: datetime | None = None
    superseded_by: str | None = None
    end_reason: str | None = None
    event_at: date | datetime | None = None
    confidence: float = 1.0
    sources: list[FactSource] = field(default_factory=list)

    @property
    def primary_source(self) -> FactSource | None:
        """The statement that opened the fact, else the earliest one."""
        for source in self.sources:
            if source.role == "opened":
                return source
        return self.sources[0] if self.sources else None

    @property
    def doc_id(self) -> str | None:
        source = self.primary_source
        return source.doc_id if source else None

    @property
    def quote(self) -> str | None:
        source = self.primary_source
        return source.quote if source else None

    @property
    def observed_at(self) -> date | datetime | None:
        source = self.primary_source
        return source.observed_at if source else None

    @property
    def is_open(self) -> bool:
        return self.valid_to is None

    def holds_at(self, when: date | datetime | str) -> bool:
        moment = to_ts(when, end_of_day=True)
        start, end = to_ts(self.valid_from), to_ts(self.valid_to)
        return (start is None or start <= moment) and (end is None or moment < end)

    def to_claim(self) -> Claim:
        """Back to P1's contract, citing the opening statement. Deadlines carry their date in
        ``valid_from`` as P1 wrote them."""

        def day(value):
            return value.date() if isinstance(value, datetime) else value

        return Claim(
            subject=self.subject, predicate=self.predicate, object=self.object,
            valid_from=day(self.event_at if self.event_at is not None else self.valid_from),
            valid_to=day(self.valid_to), observed_at=day(self.observed_at),
            doc_id=self.doc_id or "", quote=self.quote or self.content,
            confidence=self.confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id, "kind": self.kind,
            "subject": self.subject, "predicate": self.predicate, "object": self.object,
            "content": self.content,
            "valid_from": _iso(self.valid_from), "valid_to": _iso(self.valid_to),
            "event_at": _iso(self.event_at),
            "observed_at": _iso(self.observed_at),
            "recorded_at": _iso(self.recorded_at), "replaced_at": _iso(self.replaced_at),
            "superseded_by": self.superseded_by, "end_reason": self.end_reason,
            "confidence": self.confidence,
            "doc_id": self.doc_id, "quote": self.quote,
            "sources": [s.to_dict() for s in self.sources],
        }


@dataclass(slots=True)
class EntityRecord:
    entity_id: str
    name: str
    entity_type: str = "unknown"
    aliases: list[str] = field(default_factory=list)
    first_seen: date | None = None
    fact_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id, "name": self.name, "entity_type": self.entity_type,
            "aliases": self.aliases, "first_seen": _iso(self.first_seen), "fact_count": self.fact_count,
        }


@dataclass(slots=True)
class TimelineEvent:
    """A fact starting or ending inside a timeline window."""

    at: date | datetime
    change: str  # started | ended
    fact: Fact

    def to_dict(self) -> dict[str, Any]:
        return {"at": _iso(self.at), "change": self.change, "fact": self.fact.to_dict()}


@dataclass(slots=True)
class SearchHit:
    fact: Fact
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {"score": round(self.score, 4), "fact": self.fact.to_dict()}


@dataclass(slots=True)
class IngestReport:
    added: int = 0       # new facts
    merged: int = 0      # restatements or closings of an existing fact
    duplicates: int = 0  # exact claims seen before
    superseded: int = 0  # facts closed by a newer value in their slot
