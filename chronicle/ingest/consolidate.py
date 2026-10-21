"""Post-ingest consolidation: topic timelines and entity pages (``state/pages.jsonl``).

Claims are atomic and their subjects fragment: one steel delivery shows up as "hps-1",
"Harbour Point steel HPS-1" and "Order HPS-1 through HPS-5", so slot supersession never links
them and a question like "what was the ETA in between?" sees one value at a time. This pass
rebuilds the self-model idea on top of the bi-temporal store:

1. **Discover** (one LLM call per document, cached): every update to a *tracked value* the
   document states, as ``{topic, value, effective, quote}``. Quotes are checked verbatim against
   the document, as the claim extractor does, so every entry has a real source.
2. **Merge** topic names that describe the same thing (LLM, batched over blocks of names that
   share a rare word), e.g. "camden day to day" and "Camden Row: site-side oversight".
3. **Write** one timeline per topic, oldest statement first, plus the latest stated value, and
   one deterministic page per known person from their role/assignment claims.

Runs after each ingest part. Discovery is cached per document and merging per name batch, so a
re-run only pays for new documents. P2 loads ``pages.jsonl`` as ``kind="topic"``/``"entity"``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from chronicle.guard.llm_client import parse_json_reply

from .cache import DiskCache, cache_key
from .extractor import LLM, _squash, restore_quote
from .pipeline import CLAIMS_FILE, DOCS_FILE, read_claims, read_docs
from .roster import Roster
from .temporal_normalizer import resolve

PAGES_FILE = "pages.jsonl"
CONSOLIDATE_VERSION = "c1"
MERGE_BATCH = 180
# Rendered timelines keep the newest entries when a topic is very long.
MAX_ENTRIES = 24

DISCOVER_PROMPT = """\
You maintain a project memory. The document below was written on {doc_date}.
List every update it gives to a TRACKED VALUE: something whose value can change over time and
that someone may later ask about. Examples: delivery dates and ETAs, schedules, windows and
deadlines, rates and prices, quantities and counts, budgets, statuses and decisions, approvals,
who holds a role or is responsible for something, locations, versions.
Output ONLY JSON: {{"updates": [{{"topic": "...", "value": "...", "effective": "...", "quote": "..."}}]}}
- topic: a stable, specific name "<thing> - <attribute>", naming the thing as fully as the
  document allows (project, site, item ids), e.g. "Harbor Point steel HPS-1/HPS-2 - delivery ETA",
  "Camden Row - site-side day-to-day lead", "Level 3 slab pour - pour window".
  One topic per tracked value; the same value in another document should get the same name.
- value: what this document says the value is, short ("11 Aug", "GBP 1,850/day", "on hold",
  "Priya Nair"). Keep qualifiers that matter: proposed, provisional, confirmed, cancelled, moved.
- effective: the date the value takes effect or names, as written ("next Friday", "2027-08-11"),
  or null.
- quote: a VERBATIM span from the document that states the value.
- Include values the document says changed, moved, slipped, were replaced or confirmed.
- Skip greetings, chit-chat, opinions and facts that never change.
- Do NOT extract from lines starting with > (quoted text from a prior message).
If there are none, return {{"updates": []}}."""

UPDATES_SCHEMA = {
    "name": "updates",
    "schema": {
        "type": "object",
        "properties": {"updates": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "value": {"type": "string"},
                "effective": {"type": ["string", "null"]},
                "quote": {"type": "string"},
            },
            "required": ["topic", "value", "quote"],
        }}},
        "required": ["updates"],
    },
}

MERGE_PROMPT = """\
These topic names were extracted from different documents of one project corpus. Group the names
that track the SAME value: the same thing and the same attribute, even when worded differently,
abbreviated or partly named ("camden day to day" = "Camden Row - site-side day-to-day lead").
Do not merge different items (two different loads, sites or people) or different attributes of
one thing (an ETA and a cost).
Output ONLY JSON: {"groups": [{"name": "<best full name>", "members": [<ids>]}]}
List only groups with two or more members."""

MERGE_SCHEMA = {
    "name": "groups",
    "schema": {
        "type": "object",
        "properties": {"groups": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"},
                           "members": {"type": "array", "items": {"type": "integer"}}},
            "required": ["name", "members"],
        }}},
        "required": ["groups"],
    },
}

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset({
    "the", "and", "for", "with", "from", "into", "status", "date", "lead", "value", "current", "new",
    "site", "project", "team", "plan", "schedule", "window", "eta", "cost", "rate", "owner", "role",
})
# Predicates that say who holds what: the material for entity pages.
_PAGE_PREDICATES = frozenset({"role", "assigned_to", "works_on", "owns", "reports_to", "member_of",
                              "works_at", "email"})


@dataclass
class Update:
    topic: str
    value: str
    quote: str
    doc_id: str
    stated: str                # document date, ISO
    effective: str | None = None

    def key(self) -> tuple:
        return (self.stated, self.effective or "", self.doc_id, self.value)


@dataclass
class ConsolidateStats:
    documents: int = 0
    updates: int = 0
    dropped_quote: int = 0
    failed: int = 0
    topics: int = 0
    merged_names: int = 0
    entity_pages: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: list[str] = field(default_factory=list)


def _llm_variants(llm: LLM) -> dict[str, list[str]]:
    return getattr(llm, "restore_variants", lambda: {})()


def parse_updates(raw: str, key: str) -> list[dict[str, Any]]:
    """The ``key`` list from the reply's last top-level JSON value (thinking and fences tolerated)."""
    data = parse_json_reply(raw)
    items = data.get(key) if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError(f"no JSON {key} list in reply")
    return [i for i in items if isinstance(i, dict)]


def discover(doc: dict, llm: LLM, *, model: str, cache: DiskCache | None) -> tuple[list[Update], int]:
    """Tracked-value updates in one ``docs.jsonl`` row; returns (updates, dropped_for_quote)."""
    text, stated = doc["text"], doc.get("date") or ""
    key = cache_key(model, CONSOLIDATE_VERSION, "discover", stated, text)
    raw = cache.get(key) if cache else None
    if raw is None:
        messages = [{"role": "system", "content": DISCOVER_PROMPT.format(doc_date=stated)},
                    {"role": "user", "content": text}]
        try:
            raw = parse_updates(llm.complete(messages, UPDATES_SCHEMA), "updates")
        except ValueError:
            messages.append({"role": "user", "content": 'Reply with ONLY valid JSON: {"updates": [...]}'})
            raw = parse_updates(llm.complete(messages, UPDATES_SCHEMA), "updates")
        variants = _llm_variants(llm)
        haystack = _squash(text)
        for u in raw:
            if variants and isinstance(u.get("quote"), str):
                u["quote"] = restore_quote(u["quote"], haystack, variants)
        if cache:
            cache.put(key, raw)
    haystack = _squash(text)
    doc_date = date.fromisoformat(stated) if stated else None
    out, dropped = [], 0
    for u in raw:
        topic, value, quote = (str(u.get(k) or "").strip() for k in ("topic", "value", "quote"))
        if not topic or not value:
            continue
        if not quote or _squash(quote) not in haystack:
            dropped += 1
            continue
        effective = None
        if u.get("effective") and doc_date is not None:
            r = resolve(str(u["effective"]), doc_date)
            effective = r.start.isoformat() if r.start else None
        out.append(Update(topic=topic, value=value, quote=quote, doc_id=doc["doc_id"], stated=stated,
                          effective=effective))
    return out, dropped


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.casefold()) if len(w) >= 3 and w not in _STOP}


def blocks(names: list[str], batch: int = MERGE_BATCH) -> list[list[int]]:
    """Batches of name indexes, each holding names that share a rare word, so likely merges are
    seen together. Union-find over words that occur in at most 12 names; components are packed
    into batches of ``batch`` names (an oversized component is split in sorted order)."""
    words = [_words(n) for n in names]
    df = Counter(w for ws in words for w in ws)
    parent = list(range(len(names)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first: dict[str, int] = {}
    for i, ws in enumerate(words):
        for w in ws:
            if 2 <= df[w] <= 12:
                if w in first:
                    parent[find(i)] = find(first[w])
                else:
                    first[w] = i
    comps: dict[int, list[int]] = defaultdict(list)
    for i in range(len(names)):
        comps[find(i)].append(i)
    groups = sorted((sorted(c, key=lambda i: names[i].casefold()) for c in comps.values() if len(c) > 1),
                    key=len, reverse=True)
    out: list[list[int]] = []
    current: list[int] = []
    for comp in groups:
        for start in range(0, len(comp), batch):
            piece = comp[start:start + batch]
            if len(current) + len(piece) > batch:
                out.append(current)
                current = []
            current.extend(piece)
    if current:
        out.append(current)
    return out


def merge_names(names: list[str], llm: LLM, *, model: str, cache: DiskCache | None,
                stats: ConsolidateStats | None = None) -> dict[str, str]:
    """Map each topic name to its group's canonical name (names in no group map to themselves)."""
    canon = {n: n for n in names}
    for batch in blocks(names):
        listing = "\n".join(f"{j}: {names[i]}" for j, i in enumerate(batch))
        key = cache_key(model, CONSOLIDATE_VERSION, "merge", listing)
        groups = cache.get(key) if cache else None
        if groups is None:
            messages = [{"role": "system", "content": MERGE_PROMPT}, {"role": "user", "content": listing}]
            try:
                groups = parse_updates(llm.complete(messages, MERGE_SCHEMA), "groups")
            except Exception as exc:  # noqa: BLE001 - an unmerged batch only loses links
                if stats is not None:
                    stats.errors.append(f"merge: {exc}")
                continue
            if cache:
                cache.put(key, groups)
        for g in groups:
            members = [batch[m] for m in g.get("members", []) if isinstance(m, int) and 0 <= m < len(batch)]
            if len(members) < 2:
                continue
            name = str(g.get("name") or "").strip() or names[members[0]]
            for i in members:
                if canon[names[i]] == names[i]:
                    canon[names[i]] = name
    return canon


def topic_id(name: str) -> str:
    return "topic_" + hashlib.sha1(name.casefold().encode("utf-8")).hexdigest()[:12]


def render_topic(name: str, entries: list[Update]) -> str:
    """Timeline text. Each entry line starts with its statement date, so a reader (or the
    as-of filter in P3's retriever) can cut it at any day."""
    lines = [f"TOPIC: {name}"]
    for u in entries[-MAX_ENTRIES:]:
        eff = f" (effective {u.effective})" if u.effective and u.effective != u.stated else ""
        lines.append(f"- {u.stated} [{u.doc_id}]: {u.value}{eff} | \"{u.quote}\"")
    latest = entries[-1]
    values = list(dict.fromkeys(u.value for u in entries))
    if len(values) > 1:
        lines.append("VALUES IN ORDER: " + " -> ".join(values[-MAX_ENTRIES:]))
    lines.append(f"LATEST ({latest.stated}): {latest.value}")
    return "\n".join(lines)


def validate_entries(entries: list[Update], docs: dict[str, str]) -> list[Update]:
    """Keep entries whose doc_id is a known document and whose quote is verbatim in it."""
    return [u for u in entries if u.doc_id in docs and _squash(u.quote) in docs[u.doc_id]]


def build_topics(updates: list[Update], canon: dict[str, str], docs: dict[str, str]) -> list[dict]:
    grouped: dict[str, list[Update]] = defaultdict(list)
    for u in updates:
        grouped[canon.get(u.topic, u.topic)].append(u)
    pages = []
    for name, entries in grouped.items():
        entries = validate_entries(sorted(set_unique(entries), key=Update.key), docs)
        if not entries:
            continue
        pages.append({
            "kind": "topic", "page_id": topic_id(name), "title": name,
            "aliases": sorted({u.topic for u in entries} - {name}),
            "current": entries[-1].value,
            "valid_from": entries[0].stated,
            "content": render_topic(name, entries),
            "sources": [{"doc_id": u.doc_id, "quote": u.quote, "observed_at": u.stated,
                         "valid_from": u.effective} for u in entries],
        })
    return pages


def set_unique(entries: list[Update]) -> list[Update]:
    seen, out = set(), []
    for u in entries:
        k = (u.doc_id, u.value.casefold(), u.quote)
        if k not in seen:
            seen.add(k)
            out.append(u)
    return out


def build_entity_pages(claims, roster: Roster | None) -> list[dict]:
    """One page per known person: aliases and dated role/assignment statements, newest last."""
    if roster is None or not roster.people:
        return []
    aliases: dict[str, set[str]] = defaultdict(set)
    for alias, canon in roster.aliases.items():
        aliases[canon].add(alias)
    people = {p.casefold(): p for p in roster.people}
    lines: dict[str, list[tuple]] = defaultdict(list)
    for c in claims:
        if c.predicate not in _PAGE_PREDICATES and not c.predicate.startswith("attr:"):
            continue
        for side, other in ((c.subject, c.object), (c.object, c.subject)):
            person = people.get(side.casefold())
            if person:
                when = (c.valid_from or c.observed_at)
                text = f"{c.subject} {c.predicate.replace('_', ' ')} {c.object}"
                if c.valid_to:
                    text += f" (until {c.valid_to.isoformat()})"
                lines[person].append((when.isoformat() if when else "", c.doc_id, text, c.quote))
                break
    pages = []
    for person, rows in lines.items():
        rows = sorted(set(rows))[-MAX_ENTRIES:]
        al = sorted(a for a in aliases.get(person, set()) if a.casefold() != person.casefold())
        content = [f"ENTITY: {person}" + (f" (also: {', '.join(al[:8])})" if al else "")]
        content += [f"- {when} [{doc}]: {text}" for when, doc, text, _ in rows]
        pages.append({
            "kind": "entity", "page_id": "entity_" + hashlib.sha1(person.casefold().encode()).hexdigest()[:12],
            "title": person, "aliases": al, "current": "", "valid_from": rows[0][0] or None,
            "content": "\n".join(content),
            "sources": [{"doc_id": doc, "quote": quote, "observed_at": when or None, "valid_from": None}
                        for when, doc, _, quote in rows],
        })
    return pages


def consolidate(state: Path, llm: LLM, *, model: str = "nemotron", workers: int = 6,
                cache_dir: Path | None = None) -> ConsolidateStats:
    """(Re)build ``state/pages.jsonl`` from ``docs.jsonl`` and ``claims.jsonl``."""
    stats = ConsolidateStats()
    cache = DiskCache(cache_dir or state / ".llm_cache")
    docs = read_docs(state / DOCS_FILE)
    haystacks = {d["doc_id"]: _squash(d["text"]) for d in docs}

    def run(doc):
        try:
            return discover(doc, llm, model=model, cache=cache), None
        except Exception as exc:  # noqa: BLE001 - one bad document must not stop consolidation
            return None, exc

    updates: list[Update] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for doc, (found, exc) in zip(docs, pool.map(run, docs), strict=True):
            if exc is not None:
                stats.failed += 1
                print(f"[chronicle] consolidate FAILED {doc['doc_id']}: {exc}", file=sys.stderr)
                continue
            got, dropped = found
            stats.documents += 1
            stats.updates += len(got)
            stats.dropped_quote += dropped
            updates.extend(got)

    names = sorted({u.topic for u in updates}, key=str.casefold)
    canon = merge_names(names, llm, model=model, cache=cache, stats=stats)
    stats.merged_names = sum(1 for n, c in canon.items() if n != c)
    pages = build_topics(updates, canon, haystacks)
    stats.topics = len(pages)

    roster_path = state / "roster.json"
    roster = Roster.from_json(roster_path.read_text(encoding="utf-8")) if roster_path.is_file() else None
    entity_pages = build_entity_pages(read_claims(state / CLAIMS_FILE), roster)
    stats.entity_pages = len(entity_pages)

    tmp = state / (PAGES_FILE + ".tmp")
    with tmp.open("w", encoding="utf-8") as out:
        for page in pages + entity_pages:
            out.write(json.dumps(page, ensure_ascii=False) + "\n")
    tmp.replace(state / PAGES_FILE)
    stats.cache_hits, stats.cache_misses = cache.hits, cache.misses
    return stats
