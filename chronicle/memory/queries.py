"""Temporal queries over the store: as-of snapshots, entity histories and timelines.

Two clocks:

* ``as_of`` is *valid time*: what was true in the world on that day.
* ``known_at`` is *transaction time*: what Chronicle believed at that moment. Leave it out to use
  everything known now. ``as_of(d, known_at=k)`` answers "on day k, what did we think was true on
  day d?", which is how you show that a later email changed an earlier answer.

A bare date for ``as_of`` means the end of that day. Intervals are half-open, so on a handover day
the new owner holds and the old one does not.
"""

from datetime import date, datetime

from .database import MemoryDatabase, validity_clause
from .models import EntityRecord, Fact, TimelineEvent, from_ts, to_ts
from .supersession import normalize_key, normalize_predicate

When = date | datetime | str


def _filters(subject: str | None, predicate: str | None, obj: str | None, kind: str | None):
    where, params = [], []
    if subject is not None:
        where.append("subject_key = ?")
        params.append(normalize_key(subject))
    if predicate is not None:
        where.append("predicate = ?")
        params.append(normalize_predicate(predicate))
    if obj is not None:
        where.append("object_key = ?")
        params.append(normalize_key(obj))
    if kind is not None:
        where.append("kind = ?")
        params.append(kind)
    return where, params


def as_of(db: MemoryDatabase, when: When, *, known_at: When | None = None, subject: str | None = None,
          predicate: str | None = None, object: str | None = None, kind: str | None = None) -> list[Fact]:
    """Facts true at ``when``, optionally narrowed to a subject, predicate, object or kind."""
    valid, params = validity_clause(when)
    where, extra = _filters(subject, predicate, object, kind)
    return db.facts(" AND ".join([valid, *where]), [*params, *extra], known_at=known_at)


def all_facts(db: MemoryDatabase, *, known_at: When | None = None, subject: str | None = None,
              predicate: str | None = None, object: str | None = None, kind: str | None = None) -> list[Fact]:
    """Every fact regardless of when it was true, superseded ones included."""
    where, params = _filters(subject, predicate, object, kind)
    return db.facts(" AND ".join(where) or "1", params, known_at=known_at)


def value_at(db: MemoryDatabase, subject: str, predicate: str, when: When, *,
             known_at: When | None = None) -> Fact | None:
    """The single fact for ``(subject, predicate)`` at ``when``, latest start first if several."""
    found = as_of(db, when, known_at=known_at, subject=subject, predicate=predicate)
    return max(found, key=lambda f: (to_ts(f.valid_from) or ""), default=None)


def holder_at(db: MemoryDatabase, predicate: str, obj: str, when: When, *,
              known_at: When | None = None) -> Fact | None:
    """Who held ``(predicate, object)`` at ``when``: "who owned payments on 3 May?"."""
    found = as_of(db, when, known_at=known_at, predicate=predicate, object=obj)
    return max(found, key=lambda f: (to_ts(f.valid_from) or ""), default=None)


def entities(db: MemoryDatabase) -> list[EntityRecord]:
    rows = db.query(
        """SELECT e.*, (SELECT group_concat(alias, '\x1f') FROM entity_aliases a
                        WHERE a.entity_id = e.entity_id AND a.alias != e.key) AS aliases,
                  (SELECT count(*) FROM facts f WHERE f.replaced_at IS NULL
                        AND (f.subject_key = e.key OR f.object_key = e.key)) AS fact_count
           FROM entities e ORDER BY e.name COLLATE NOCASE"""
    )
    return [_entity(r) for r in rows]


def find_entity(db: MemoryDatabase, id_or_name: str) -> EntityRecord | None:
    """Look an entity up by ``entity_id``, canonical name or any alias."""
    key = normalize_key(id_or_name)
    for record in entities(db):
        if record.entity_id == id_or_name or normalize_key(record.name) == key or key in record.aliases:
            return record
    return None


def history(db: MemoryDatabase, entity: str, *, known_at: When | None = None) -> list[Fact]:
    """Every fact about an entity (as subject or object, under any alias), oldest first."""
    record = find_entity(db, entity)
    keys = {normalize_key(entity)}
    if record:
        keys |= {normalize_key(record.name), *record.aliases}
    marks = ",".join("?" * len(keys))
    return db.facts(f"subject_key IN ({marks}) OR object_key IN ({marks})", [*keys, *keys], known_at=known_at)


def timeline(db: MemoryDatabase, start: When, end: When, *, known_at: When | None = None,
             entity: str | None = None) -> list[TimelineEvent]:
    """Facts starting or ending between ``start`` and ``end`` (inclusive days), in date order."""
    lo, hi = to_ts(start), to_ts(end, end_of_day=True)
    facts = history(db, entity, known_at=known_at) if entity else db.facts(
        "(valid_from BETWEEN ? AND ?) OR (valid_to BETWEEN ? AND ?)", [lo, hi, lo, hi], known_at=known_at)
    events = []
    for fact in facts:
        for change, moment in (("started", fact.valid_from), ("ended", fact.valid_to)):
            if moment is not None and lo <= to_ts(moment) <= hi:
                events.append(TimelineEvent(moment, change, fact))
    events.sort(key=lambda e: (to_ts(e.at), e.change == "started"))
    return events


def span(db: MemoryDatabase) -> tuple[date | None, date | None]:
    """First and last day the store has any dated statement for (the UI's slider range)."""
    row = db.query(
        """SELECT MIN(m) AS lo, MAX(m) AS hi FROM (
             SELECT valid_from AS m FROM fact_sources UNION ALL SELECT valid_to FROM fact_sources
             UNION ALL SELECT observed_at FROM fact_sources)"""
    )[0]
    lo, hi = from_ts(row["lo"], "day"), from_ts(row["hi"], "day")
    return lo, hi


def _entity(row) -> EntityRecord:
    return EntityRecord(
        entity_id=row["entity_id"], name=row["name"], entity_type=row["entity_type"],
        aliases=row["aliases"].split("\x1f") if row["aliases"] else [],
        first_seen=from_ts(row["first_seen"], "day"), fact_count=row["fact_count"],
    )
