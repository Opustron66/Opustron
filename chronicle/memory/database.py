"""SQLite storage for the bi-temporal fact store.

``MemoryDatabase`` owns the connection, the schema migrations and the write path. Every write
goes through a transaction and appends rows; a fact's validity changes by closing its current
version (``replaced_at``) and inserting a new one, so the store can always answer "what did we
believe on day X" as well as "what was true on day X".

Reads that callers need live in ``queries`` and ``search``; ``api.MemoryAPI`` puts it together.
"""

import hashlib
import sqlite3
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from chronicle.schema import Claim
from chronicle.claim_normalization import normalize_claim_value

from .models import Fact, FactSource, from_ts, to_ts
from .supersession import (
    DATED,
    SlotMember,
    normalize_key,
    normalize_predicate,
    resolve_slot,
    slot_for,
)

MIGRATIONS = Path(__file__).parent / "migrations"

# Predicates whose object is a value ("blocked", "due", "staff engineer"), not an entity.
LITERAL_OBJECT = frozenset({"status", "email", "deadline", "scheduled_for", "role", "title", "decided", "proposed", "completed"})
# Predicates whose subject is a person.
PERSON_SUBJECT = frozenset({"owns", "email", "works_on", "works_at", "reports_to", "member_of", "role", "leads", "manages"})

_VERSION_FIELDS = ("valid_from", "valid_to", "superseded_by", "end_reason")


def claim_hash(claim: Claim) -> str:
    return hashlib.sha256(claim.model_dump_json().encode("utf-8")).hexdigest()


def entity_id_for(key: str) -> str:
    return "ent_" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def version_clause(known_at: date | datetime | str | None) -> tuple[str, list[Any]]:
    """SQL selecting the row version of each fact that was believed at ``known_at`` (now if None)."""
    if known_at is None:
        return "replaced_at IS NULL", []
    moment = to_ts(known_at, end_of_day=True)
    return "recorded_at <= ? AND (replaced_at IS NULL OR replaced_at > ?)", [moment, moment]


def validity_clause(as_of: date | datetime | str) -> tuple[str, list[Any]]:
    """SQL for facts true at ``as_of``. A bare date means the end of that day."""
    moment = to_ts(as_of, end_of_day=True)
    return "(valid_from IS NULL OR valid_from <= ?) AND (valid_to IS NULL OR valid_to > ?)", [moment, moment]


class MemoryDatabase:
    """A SQLite file (or ``":memory:"``) holding facts, their sources and entities.

    Safe to share across threads: one connection, guarded by a lock. ``clock`` is injectable so
    tests can control transaction time.
    """

    def __init__(self, path: str | Path = ":memory:", *, clock: Callable[[], datetime] | None = None) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._depth = 0
        self._clock = clock or (lambda: datetime.now(UTC))
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        if self.path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL")
        self.migrate()

    # -- plumbing ------------------------------------------------------------------------------

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def now(self) -> str:
        return to_ts(self._clock())

    @property
    def schema_version(self) -> int:
        return self._conn.execute("PRAGMA user_version").fetchone()[0]

    def migrate(self) -> None:
        """Apply ``migrations/NNNN_*.sql`` files newer than the database's ``user_version``."""
        with self._lock:
            current = self.schema_version
            for script in sorted(MIGRATIONS.glob("[0-9][0-9][0-9][0-9]_*.sql")):
                number = int(script.name[:4])
                if number <= current:
                    continue
                self._conn.executescript(
                    f"BEGIN;\n{script.read_text(encoding='utf-8')}\nPRAGMA user_version = {number};\nCOMMIT;"
                )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            outer = self._depth == 0
            if outer:
                self._conn.execute("BEGIN IMMEDIATE")
            self._depth += 1
            try:
                yield self._conn
            except BaseException:
                self._depth -= 1
                if outer:
                    self._conn.execute("ROLLBACK")
                raise
            self._depth -= 1
            if outer:
                self._conn.execute("COMMIT")

    def query(self, sql: str, params: list[Any] | tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchall()

    # -- reads ---------------------------------------------------------------------------------

    def facts(self, where: str = "1", params: list[Any] | None = None, *, known_at=None,
              order: str = "valid_from IS NOT NULL, valid_from, row_id") -> list[Fact]:
        """Fact versions matching ``where`` as believed at ``known_at``, sources attached."""
        version, version_params = version_clause(known_at)
        rows = self.query(
            f"SELECT * FROM facts WHERE {version} AND ({where}) ORDER BY {order}",
            [*version_params, *(params or [])],
        )
        return self._hydrate(rows, known_at=known_at)

    def versions(self, fact_id: str) -> list[Fact]:
        """Every recorded version of one fact, oldest first (the transaction-time audit trail)."""
        rows = self.query("SELECT * FROM facts WHERE fact_id = ? ORDER BY row_id", [fact_id])
        return self._hydrate(rows)

    def _hydrate(self, rows: list[sqlite3.Row], *, known_at=None) -> list[Fact]:
        if not rows:
            return []
        ids = sorted({r["fact_id"] for r in rows})
        sql = f"SELECT * FROM fact_sources WHERE fact_id IN ({','.join('?' * len(ids))})"
        params: list[Any] = list(ids)
        if known_at is not None:
            sql += " AND recorded_at <= ?"
            params.append(to_ts(known_at, end_of_day=True))
        sources: dict[str, list[FactSource]] = {}
        for s in self.query(sql + " ORDER BY observed_at IS NULL, observed_at, source_id", params):
            sources.setdefault(s["fact_id"], []).append(FactSource(
                doc_id=s["doc_id"], quote=s["quote"], role=s["role"], uri=s["uri"],
                observed_at=from_ts(s["observed_at"], "day" if _is_day(s["observed_at"]) else "instant"),
                valid_from=from_ts(s["valid_from"], "day" if _is_day(s["valid_from"]) else "instant"),
                valid_to=from_ts(s["valid_to"], "day" if _is_day(s["valid_to"]) else "instant"),
                confidence=s["confidence"], recorded_at=from_ts(s["recorded_at"]),
            ))
        return [
            Fact(
                fact_id=r["fact_id"], kind=r["kind"], subject=r["subject"], predicate=r["predicate"],
                object=r["object"], content=r["content"],
                valid_from=from_ts(r["valid_from"], r["granularity"]),
                valid_to=from_ts(r["valid_to"], r["granularity"]),
                event_at=from_ts(r["event_at"], r["granularity"]),
                granularity=r["granularity"], recorded_at=from_ts(r["recorded_at"]),
                replaced_at=from_ts(r["replaced_at"]), superseded_by=r["superseded_by"],
                end_reason=r["end_reason"], confidence=r["confidence"],
                sources=sources.get(r["fact_id"], []),
            )
            for r in rows
        ]

    # -- claims (P1) ---------------------------------------------------------------------------

    def add_claim(self, claim: Claim, *, uri: str | None = None) -> tuple[str, str, int]:
        """Store one P1 claim. Returns ``(outcome, fact_id, newly_superseded)``.

        ``outcome`` is ``added`` (a new fact), ``merged`` (a restatement or the closing of a fact
        already stored) or ``duplicate`` (this exact claim was ingested before; nothing changes).
        """
        digest = claim_hash(claim)
        with self.transaction() as conn:
            seen = conn.execute("SELECT fact_id FROM fact_sources WHERE claim_hash = ?", [digest]).fetchone()
            if seen:
                return "duplicate", seen["fact_id"], 0
            now = self.now()
            subject, obj = claim.subject.strip(), claim.object.strip()
            predicate = normalize_predicate(claim.predicate)
            predicate, obj = normalize_claim_value(predicate, obj)
            s_key, o_key = normalize_key(subject), normalize_key(obj)
            dated = predicate in DATED and claim.valid_from is not None
            event_at = to_ts(claim.valid_from) if dated else None
            closing = claim.valid_from is None and claim.valid_to is not None
            if dated:
                start = to_ts(claim.observed_at or claim.valid_from)
            elif claim.valid_from is not None:
                start = to_ts(claim.valid_from)
            else:  # P1 leaves valid_from empty only on closing claims: the start is unknown
                start = None if closing else to_ts(claim.observed_at)
            end = to_ts(claim.valid_to)
            if start is not None and end is not None and end < start:
                start = None  # contradictory dates: trust the explicit end
            spo = f"{s_key}|{predicate}|{o_key}" + (f"@{event_at}" if event_at else "")
            slot, value = slot_for(s_key, predicate, o_key)
            if slot and dated:
                value = f"{value}@{event_at}"

            fact_id = self._join_target(spo, slot, value, start, end, closing)
            outcome = "merged"
            if fact_id is None:
                outcome, fact_id = "added", "fact_" + uuid4().hex[:16]
                content = f"{subject} {predicate.replace('_', ' ')} {obj}"
                if dated:
                    content += f" on {claim.valid_from.isoformat()}"
                conn.execute(
                    """INSERT INTO facts (fact_id, kind, subject, predicate, object, subject_key, object_key,
                       content, spo_key, event_at, slot, value_key, valid_from, valid_to, granularity, end_reason,
                       confidence, recorded_at)
                       VALUES (?, 'claim', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'day', ?, ?, ?)""",
                    [fact_id, subject, predicate, obj, s_key, o_key, content, spo, event_at, slot, value, start, end,
                     "stated" if end else None, claim.confidence, now],
                )
            has_opening = conn.execute(
                "SELECT 1 FROM fact_sources WHERE fact_id = ? AND role = 'opened'", [fact_id]
            ).fetchone()
            role = "closed" if closing else ("restated" if has_opening else "opened")
            conn.execute(
                """INSERT INTO fact_sources (fact_id, claim_hash, role, doc_id, uri, quote, observed_at,
                   valid_from, valid_to, confidence, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [fact_id, digest, role, claim.doc_id, uri, claim.quote, to_ts(claim.observed_at),
                 start, end, claim.confidence, now],
            )
            superseded = self._refresh(fact_id, slot, now)
            first_seen = to_ts(claim.observed_at)
            self._upsert_entity(subject, "person" if predicate in PERSON_SUBJECT else "unknown", first_seen, now)
            if predicate not in LITERAL_OBJECT:
                self._upsert_entity(obj, "unknown", first_seen, now)
            return outcome, fact_id, superseded

    def _current(self, where: str, params: list[Any]) -> list[sqlite3.Row]:
        return self._conn.execute(f"SELECT * FROM facts WHERE replaced_at IS NULL AND ({where})", params).fetchall()

    def _join_target(self, spo, slot, value, start, end, closing) -> str | None:
        """Pick the stored fact this claim restates or closes, if any.

        A closing claim joins the latest same-triple fact that started before the close. An
        opening claim joins a same-triple fact whose interval contains its start, or the next
        one to start after it when no rival value in the slot starts in between (an earlier
        mention ingested after a later one).
        """
        candidates = self._current("spo_key = ?", [spo])
        if not candidates:
            return None
        if closing:
            before = [c for c in candidates if c["valid_from"] is None or c["valid_from"] < end]
            best = max(before, key=lambda c: c["valid_from"] or "", default=None)
            return best["fact_id"] if best else None
        for c in candidates:
            if start is None or ((c["valid_from"] is None or c["valid_from"] <= start)
                                 and (c["valid_to"] is None or start < c["valid_to"])):
                return c["fact_id"]
        later = sorted((c for c in candidates if c["valid_from"] is not None and c["valid_from"] > start),
                       key=lambda c: c["valid_from"])
        for c in later:
            if end is not None and end < c["valid_from"]:
                break
            if slot and self._current(
                "slot = ? AND value_key != ? AND valid_from >= ? AND valid_from < ?",
                [slot, value, start, c["valid_from"]],
            ):
                break
            return c["fact_id"]
        return None

    def _refresh(self, fact_id: str, slot: str | None, now: str) -> int:
        """Recompute validity for a fact (and its slot) from sources; version anything that moved."""
        ids = [fact_id] if slot is None else [r["fact_id"] for r in self._current("slot = ?", [slot])]
        marks = ",".join("?" * len(ids))
        stated = {
            r["fact_id"]: r for r in self._conn.execute(
                f"""SELECT fact_id, MIN(valid_from) AS start, MIN(valid_to) AS stated_end,
                    MIN(CASE WHEN role != 'closed' THEN observed_at END) AS observed
                    FROM fact_sources WHERE fact_id IN ({marks}) GROUP BY fact_id""", ids,
            )
        }
        rows = {r["fact_id"]: r for r in self._current(f"fact_id IN ({marks})", ids)}
        seq = {r["fact_id"]: r["seq"] for r in self._conn.execute(
            f"SELECT fact_id, MIN(row_id) AS seq FROM facts WHERE fact_id IN ({marks}) GROUP BY fact_id", ids)}
        members = [
            SlotMember(fid, rows[fid]["value_key"] or fid, stated[fid]["start"], stated[fid]["stated_end"],
                       "stated", stated[fid]["observed"], seq[fid])
            for fid in ids
        ]
        newly_superseded = 0
        for fid, res in resolve_slot(members).items():
            start = stated[fid]["start"]
            desired = {"valid_from": start, "valid_to": res.valid_to,
                       "superseded_by": res.superseded_by, "end_reason": res.end_reason}
            if rows[fid]["superseded_by"] is None and res.superseded_by is not None:
                newly_superseded += 1
            self._revise(rows[fid], desired, now)
        return newly_superseded

    def _revise(self, row: sqlite3.Row, changes: dict[str, Any], now: str) -> None:
        if all(row[k] == v for k, v in changes.items()):
            return
        skip = ("row_id", "recorded_at", "replaced_at")
        fields = {k: row[k] for k in row.keys() if k not in skip}  # noqa: SIM118 (Row iterates values)
        fields.update(changes)
        self._conn.execute("UPDATE facts SET replaced_at = ? WHERE row_id = ?", [now, row["row_id"]])
        cols = [*fields, "recorded_at"]
        self._conn.execute(
            f"INSERT INTO facts ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
            [*fields.values(), now],
        )

    def _upsert_entity(self, name: str, entity_type: str, first_seen: str | None, now: str) -> None:
        key = normalize_key(name)
        if not key:
            return
        existing = self._conn.execute(
            "SELECT e.* FROM entity_aliases a JOIN entities e USING (entity_id) WHERE a.alias = ?", [key]
        ).fetchone()
        if existing is None:
            entity_id = entity_id_for(key)
            self._conn.execute(
                "INSERT OR IGNORE INTO entities (entity_id, name, key, entity_type, first_seen, recorded_at) "
                "VALUES (?, ?, ?, ?, ?, ?)", [entity_id, name, key, entity_type, first_seen, now],
            )
            self._conn.execute("INSERT OR IGNORE INTO entity_aliases (alias, entity_id) VALUES (?, ?)", [key, entity_id])
            return
        updates: dict[str, Any] = {}
        if existing["entity_type"] == "unknown" and entity_type != "unknown":
            updates["entity_type"] = entity_type
        if first_seen and (existing["first_seen"] is None or first_seen < existing["first_seen"]):
            updates["first_seen"] = first_seen
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            self._conn.execute(f"UPDATE entities SET {sets} WHERE entity_id = ?", [*updates.values(), existing["entity_id"]])

    def add_alias(self, alias: str, name: str) -> None:
        """Point another surface form at an existing entity (creating the entity if needed)."""
        with self.transaction() as conn:
            now = self.now()
            self._upsert_entity(name, "unknown", None, now)
            entity_id = conn.execute(
                "SELECT entity_id FROM entity_aliases WHERE alias = ?", [normalize_key(name)]
            ).fetchone()["entity_id"]
            conn.execute("INSERT OR REPLACE INTO entity_aliases (alias, entity_id) VALUES (?, ?)",
                         [normalize_key(alias), entity_id])

    # -- notes (Hermes) ------------------------------------------------------------------------

    def add_note(self, content: str, *, source: str, at: datetime | None = None,
                 supersedes: str | None = None) -> str:
        """Store a free-text fact true from ``at``; optionally close an earlier note at ``at``."""
        with self.transaction() as conn:
            now = self.now()
            start = to_ts(at) if at is not None else now
            fact_id = "fact_" + uuid4().hex[:16]
            conn.execute(
                """INSERT INTO facts (fact_id, kind, subject, predicate, object, subject_key, object_key, content,
                   spo_key, valid_from, granularity, recorded_at)
                   VALUES (?, 'note', '', '', '', '', '', ?, ?, ?, 'instant', ?)""",
                [fact_id, content, "note|" + normalize_key(content), start, now],
            )
            self._note_source(fact_id, "opened", source, content, start, start, None, now)
            if supersedes:
                self._close_notes(supersedes, start, by=fact_id, reason="superseded", source=source, now=now)
            return fact_id

    def retire_note(self, content_or_id: str, *, at: datetime, source: str = "retire") -> int:
        with self.transaction():
            return self._close_notes(content_or_id, to_ts(at), by=None, reason="retired", source=source, now=self.now())

    def _close_notes(self, content_or_id, end, *, by, reason, source, now) -> int:
        rows = self._current(
            "kind = 'note' AND valid_to IS NULL AND fact_id != ? AND (fact_id = ? OR spo_key = ?)",
            [by or "", content_or_id, "note|" + normalize_key(content_or_id)],
        )
        for row in rows:
            self._note_source(row["fact_id"], "closed", source, row["content"], end, None, end, now)
            self._revise(row, {"valid_to": end, "superseded_by": by, "end_reason": reason}, now)
        return len(rows)

    def _note_source(self, fact_id, role, source, quote, observed, start, end, now) -> None:
        self._conn.execute(
            """INSERT INTO fact_sources (fact_id, claim_hash, role, doc_id, uri, quote, observed_at,
               valid_from, valid_to, recorded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [fact_id, uuid4().hex, role, source, source, quote, observed, start, end, now],
        )


def _is_day(ts: str | None) -> bool:
    return ts is not None and ts[10:26] == "T00:00:00.000000"
