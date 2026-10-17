"""LLM claim extraction: Document -> atomic, source-dated Claims."""

import json
import re
import threading
from typing import Any, Protocol

from chronicle.schema import Claim, Document, Entity, Event

from .cache import DiskCache, cache_key
from .temporal_normalizer import NormalizerConfig, resolve

PROMPT_VERSION = "v1"

PREDICATES = [
    "owns", "works_on", "works_at", "reports_to", "status", "deadline", "scheduled_for",
    "located_in", "decided", "proposed", "completed", "blocked_by", "member_of", "role", "related_to",
]

SYSTEM_PROMPT = f"""You extract atomic factual claims from one document.
The document was written on {{doc_date}}. Resolve every relative date ("next Friday", "yesterday")
against THAT date, never today's date. Output ONLY JSON: {{"claims": [...]}} with no commentary.
Each claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).
- One fact per claim. Subject/object are canonical entity names (no pronouns).
- predicate: one of {PREDICATES} (use related_to only if nothing fits).
- valid_from / valid_to: the date expression exactly as written in the text (e.g. "next Friday",
  "2026-05-12", "today") or null. valid_from = when the fact starts being true; valid_to = when it ends.
- Deadlines and scheduled events: subject = the thing, predicate = deadline/scheduled_for,
  object = a short description of what is due or happening (NOT the date), and the date goes in
  valid_from. Example: "The migration is due next Friday" -> subject "migration", predicate
  "deadline", object "due", valid_from "next Friday", valid_to null.
- Changes of ownership/role (takeovers, handovers, reassignments) need TWO claims:
  1. the NEW state: new person, predicate owns (or role/works_on), the thing, valid_from = the
     effective date ("today" if "effective today"), valid_to null;
  2. the OLD state ending: old person, same predicate, same thing, valid_from null, valid_to = the
     same effective date.
  Example: "Effective today, Dana takes over payments from Alice" -> (Dana, owns, payments,
  valid_from "today", null) and (Alice, owns, payments, null, valid_to "today").
- quote: a VERBATIM span copied from the document that supports the claim; reuse the same quote
  for both claims of a change.
- Include who proposed vs who did when the text distinguishes them (predicate proposed vs completed).
- Do not invent facts the document does not state. If there are none, return {{"claims": []}}."""

CLAIMS_SCHEMA = {
    "name": "claims",
    "schema": {
        "type": "object",
        "properties": {"claims": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"}, "predicate": {"type": "string"}, "object": {"type": "string"},
                "valid_from": {"type": ["string", "null"]}, "valid_to": {"type": ["string", "null"]},
                "quote": {"type": "string"}, "confidence": {"type": "number"},
            },
            "required": ["subject", "predicate", "object", "quote"],
        }}},
        "required": ["claims"],
    },
}


class LLM(Protocol):
    """Minimal interface P1 needs; P4's ``guard.llm_client`` provides the real one."""

    def complete(self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None) -> str: ...


def parse_llm_json(raw: str) -> list[dict[str, Any]]:
    """Tolerantly parse the model's reply.

    Reasoning models (e.g. Nemotron 3.5 Lightning) may emit visible thinking text that itself
    contains braces. We strip <think> blocks and code fences, then take the LAST decodable JSON
    value that holds a claims list, since the final answer follows the reasoning.
    """
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text)
    decoder, found = json.JSONDecoder(), None
    for m in re.finditer(r"[{\[]", text):
        try:
            data, _ = decoder.raw_decode(text[m.start():])
        except ValueError:
            continue
        claims = data.get("claims") if isinstance(data, dict) else data
        if isinstance(claims, list):
            found = claims
    if found is None:
        raise ValueError("no JSON claims list in reply")
    return [c for c in found if isinstance(c, dict)]


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


class ClaimExtractor:
    def __init__(self, llm: LLM, *, model: str = "nemotron", cache: DiskCache | None = None,
                 config: NormalizerConfig | None = None) -> None:
        self.llm, self.model, self.cache, self.config = llm, model, cache, config
        self.dropped = 0  # claims rejected (hallucinated quote / invalid)
        self._lock = threading.Lock()

    def _raw_claims(self, doc: Document) -> list[dict[str, Any]]:
        key = cache_key(self.model, PROMPT_VERSION, doc.doc_date.isoformat() if doc.doc_date else "", doc.text)
        if self.cache and (hit := self.cache.get(key)) is not None:
            return hit
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{doc_date}", str(doc.doc_date))},
            {"role": "user", "content": doc.text},
        ]
        try:
            raw = parse_llm_json(self.llm.complete(messages, CLAIMS_SCHEMA))
        except ValueError:  # one repair retry
            messages.append({"role": "user", "content": 'Reply with ONLY valid JSON: {"claims": [...]}'})
            raw = parse_llm_json(self.llm.complete(messages, CLAIMS_SCHEMA))
        if self.cache:
            self.cache.put(key, raw)
        return raw

    def extract(self, doc: Document) -> list[Claim]:
        if doc.doc_date is None:
            raise ValueError(f"{doc.doc_id}: document has no date; refusing to stamp with ingestion time")
        haystack = _squash(doc.text)
        claims = []
        for c in self._raw_claims(doc):
            quote = str(c.get("quote") or "").strip()
            if not all(c.get(k) for k in ("subject", "predicate", "object")) or _squash(quote) not in haystack or not quote:
                with self._lock:
                    self.dropped += 1
                continue
            start = resolve(c.get("valid_from"), doc.doc_date, config=self.config)
            end = resolve(c.get("valid_to"), doc.doc_date, config=self.config)
            conf = float(c.get("confidence") or 1.0)
            if c.get("valid_from") and start.start is None:
                conf = min(conf, 0.4)
            claims.append(Claim(
                subject=str(c["subject"]).strip(), predicate=str(c["predicate"]).strip().lower(),
                object=str(c["object"]).strip(), valid_from=start.start or (None if end.start else doc.doc_date),  # closing claim: start unknown
                valid_to=end.start if end.start else None, observed_at=doc.doc_date,
                doc_id=doc.doc_id, quote=quote, confidence=max(0.0, min(1.0, conf * min(start.confidence or 1, 1))),
            ))
        return claims


def extract_entities(event: Event) -> list[Entity]:
    """Return a conservative set of capitalized names from event content (legacy heuristic)."""
    words = event.content.replace(",", " ").split()
    names = []
    for word in words:
        candidate = word.strip(".!?():;\"'")
        if candidate and candidate[0].isupper() and candidate not in {"The", "A", "I", "Met"}:
            names.append(Entity(name=candidate))
    return names
