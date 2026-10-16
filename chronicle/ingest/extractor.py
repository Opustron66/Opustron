"""LLM claim extraction: Document -> atomic, source-dated Claims."""

import json
import re
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
against THAT date, never today's date. Output ONLY JSON: {{"claims": [...]}}.
Each claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).
- One fact per claim. Subject/object are canonical entity names (no pronouns).
- predicate: one of {PREDICATES} (use related_to only if nothing fits).
- valid_from/valid_to: the date expression exactly as written in the text (e.g. "next Friday",
  "2026-05-12") or null. valid_from = when the fact starts being true; valid_to = when it ends.
  If the document says something changes "effective today", valid_from is "today".
- quote: a VERBATIM span copied from the document that supports the claim.
- Include who said/proposed vs who did when the text distinguishes them (predicate proposed vs completed).
- Do not invent facts that the document does not state."""

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
    """Tolerantly parse the model's reply (strips code fences / <think> blocks)."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        raise ValueError("no JSON in reply")
    data, _ = json.JSONDecoder().raw_decode(text[start:])
    claims = data.get("claims") if isinstance(data, dict) else data
    if not isinstance(claims, list):
        raise ValueError("reply has no claims list")
    return [c for c in claims if isinstance(c, dict)]


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


class ClaimExtractor:
    def __init__(self, llm: LLM, *, model: str = "nemotron", cache: DiskCache | None = None,
                 config: NormalizerConfig | None = None) -> None:
        self.llm, self.model, self.cache, self.config = llm, model, cache, config
        self.dropped = 0  # claims rejected (hallucinated quote / invalid)

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
                self.dropped += 1
                continue
            start = resolve(c.get("valid_from"), doc.doc_date, config=self.config)
            end = resolve(c.get("valid_to"), doc.doc_date, config=self.config)
            conf = float(c.get("confidence") or 1.0)
            if c.get("valid_from") and start.start is None:
                conf = min(conf, 0.4)
            claims.append(Claim(
                subject=str(c["subject"]).strip(), predicate=str(c["predicate"]).strip().lower(),
                object=str(c["object"]).strip(), valid_from=start.start or doc.doc_date,
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
