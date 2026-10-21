"""LLM claim extraction: Document -> atomic, source-dated Claims."""

import json
import re
import threading
from collections import Counter
from typing import Any, Protocol

from chronicle.schema import Claim, Document, Entity, Event
from chronicle.claim_normalization import DATED_PREDICATES, normalize_claim_value

from .cache import DiskCache, cache_key
from .roster import Roster
from .temporal_normalizer import NormalizerConfig, resolve

# v5: quotes restored to the spelling the document used (no prompt change).
PROMPT_VERSION = "v5"

# Controlled predicate vocabulary.  ``related_to`` is intentionally absent.
PREDICATES = [
    "owns", "role", "works_on", "works_at", "member_of", "reports_to", "assigned_to",
    "status", "decided", "proposed", "completed", "requested",
    "deadline", "scheduled_for", "located_in", "blocked_by", "email",
]
# attr:<snake_key> is also valid (e.g. attr:budget, attr:p95_latency)
_ATTR_RE = re.compile(r"^attr:[a-z0-9_]+$")

# Near-miss synonyms the model sometimes uses -> canonical predicate
PREDICATE_SYNONYMS: dict[str, str] = {
    "organized_by": "owns",
    "organizer": "owns",
    "owns_by": "owns",
    "led_by": "owns",
    "managed_by": "owns",
    "invitee": "member_of",
    "attendee": "member_of",
    "assigned": "assigned_to",
    "assigned_to_person": "assigned_to",
    "taking_over": "owns",
    "takes_over": "owns",
    "handover": "owns",
    "is_blocked_by": "blocked_by",
    "blocks": "blocked_by",
    "approved": "decided",
    "rejected": "decided",
    "presented": "proposed",
    "owns_role": "role",
    "has_role": "role",
    "due": "deadline",
    # rename / refactoring suggestions
    "proposed_rename": "proposed",
    "renamed_to": "decided",
    "renamed": "decided",
    "refactored_to": "decided",
    "moved_to": "decided",
    "changed_to": "decided",
    # contact details
    "work_email": "email",
    "contact_email": "email",
    "email_address": "email",
}

# Subjects that look like code artefacts rather than entities
_NON_ENTITY_RE = re.compile(
    r"^(https?://|/[\w/]|\.{0,2}/|`|\!?\d+|[A-Za-z0-9]{7,40}(?:[A-Za-z]\d|\d[A-Za-z])[A-Za-z0-9]{7,}$)"
)
# MR / issue / PR normaliser
_MR_RE = re.compile(r"^[!#](\d+)$")

# Bot / automated-sender patterns
_BOT_FROM = re.compile(r"(gitlab|review-bot|metricswatch|no-reply|noreply|ops-notifications|itsupport)",
                       re.IGNORECASE)

_SYSTEM_BASE = """\
The document was written on {doc_date}. Resolve every relative date ("next Friday", "yesterday")
against THAT date, never today's date. Output ONLY JSON: {{"claims": [...]}} with no commentary.
Each claim: subject, predicate, object, valid_from, valid_to, quote, confidence (0-1).
- One fact per claim. Subject/object are canonical entity names (no pronouns).
- predicate: one of {predicates}
  or attr:<snake_key> for measured values (e.g. attr:budget, attr:p95_latency).
  Use attr:<key> only when the document states a specific value.
  Do NOT use related_to — if nothing fits, omit the claim.
- valid_from / valid_to: the date expression exactly as written (e.g. "next Friday",
  "2026-05-12", "today") or null. valid_from = when the fact starts; valid_to = when it ends.
- Deadlines/scheduled events: subject = the thing, predicate = deadline/scheduled_for,
  object = short description of what is due, date goes in valid_from.
  Example: "migration due next Friday" -> subject "migration", predicate "deadline",
  object "due", valid_from "next Friday", valid_to null.
  Use object "due" for deadlines and "scheduled" for scheduled events; keep the event
  description in subject.
- A rescheduled deadline/event needs ONLY its new date. Do not emit a closing claim ending
  on the old date: the store supersedes the old schedule when this document states the new one.
- An explicit cancellation is a status claim with object "cancelled" and valid_from = the
  effective cancellation date, not a deadline ending on its old date.
- Contact email: predicate email, object the exact address. Never use status for an email.
- Changes of ownership/role/assignment need TWO claims:
  1. NEW state: new person, predicate (owns/role/assigned_to), the thing,
     valid_from = effective date, valid_to null.
  2. OLD state ending: old person, same predicate, same thing,
     valid_from null, valid_to = same effective date.
  Use the same verbatim quote for both.
- quote: a VERBATIM span from the document supporting the claim.
  Quotes from the document header (From/To/Subject lines) are valid.
- Include who proposed vs who completed when the text distinguishes them.
- Do NOT extract from lines starting with > (quoted text from a prior message).
- Do not invent facts the document does not state. If there are none, return {{"claims": []}}.\
"""

SYSTEM_PROMPT_HUMAN = (
    "You extract atomic factual claims from one document.\n"
    + _SYSTEM_BASE
    + """
Priority order — extract FIRST:
  1. Ownership/role/assignment changes (paired new+old as described above)
  2. Decisions, proposals, completions
  3. Status changes and blockers
  4. Deadlines and scheduled events
  5. Numeric/config values (attr:)
  6. Stable facts (membership, location, reporting lines)
Skip greetings, opinions, reactions, and chit-chat.\
"""
)

SYSTEM_PROMPT_AUTOMATED = (
    "You extract factual events from an automated notification.\n"
    + _SYSTEM_BASE
    + """
Extract at most 5 claims, only for significant events:
  - MR/PR opened, merged, or closed: who + which item -> predicate proposed/completed/status
  - Pipeline or build failed/passed -> status
  - Incident opened/resolved -> status
  - Alert threshold crossed -> attr:<metric>
Do NOT extract: file lists, commit messages, diff stats, code snippets, review comments.\
"""
)

CLAIMS_SCHEMA = {
    "name": "claims",
    "schema": {
        "type": "object",
        "properties": {"claims": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "subject": {"type": "string"},
                "predicate": {"type": "string"},
                "object": {"type": "string"},
                "valid_from": {"type": ["string", "null"]},
                "valid_to": {"type": ["string", "null"]},
                "quote": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["subject", "predicate", "object", "quote"],
        }}},
        "required": ["claims"],
    },
}

# Strips Slack rendering noise:
#   [2026-04-21T15:00:24Z]   ISO timestamp prefix at line start
#   (U200C6EF237B)           Slack user-id token in speaker prefix
#   [ts=…]                   raw ts= marker
#   (thread reply to …)      thread-reply annotation
_TS_NOISE = re.compile(
    r"^\s*\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]\s*"  # leading ISO timestamp
    r"|\s*\(U[A-Z0-9]{6,20}\)"                            # slack user-id (Uxxx)
    r"|\s*\[ts=[^\]]+\]"                                  # [ts=…]
    r"|\s*\(thread reply to [^)]+\)",                     # thread-reply note
    re.MULTILINE,
)


class LLM(Protocol):
    """Minimal interface P1 needs; ``chronicle.guard.LLMClient`` provides the real one.

    Given the ``json_schema`` envelope ``CLAIMS_SCHEMA``, the guard client returns the raw
    reply text with pseudonyms already restored, so quotes still match the document.
    """

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
    """Quote-check normaliser: keeps only letters/digits so markdown (bold, links, bullets,
    backticks) and whitespace differences never cause a faithful quote to be rejected."""
    return re.sub(r"[\W_]+", "", re.sub(r"\]\([^)]*\)", "", s)).lower()


def restore_quote(quote: str, haystack: str, variants: dict[str, list[str]]) -> str:
    """Return ``quote`` re-spelled so it matches the document, or unchanged if it can't be.

    The privacy router restores every pseudonym to the entity's full name, but the document may
    have said "camden" or "Camden Row's". Try each restored name's other spellings, one name
    at a time and then together, until the squashed quote is found in the squashed document.
    """
    if not variants or _squash(quote) in haystack:
        return quote
    present = [v for v in sorted(variants, key=len, reverse=True)
               if re.search(re.escape(v), quote, re.IGNORECASE)]
    candidates = [quote]
    for value in present[:4]:
        pattern = re.compile(re.escape(value), re.IGNORECASE)
        candidates += [pattern.sub(lambda _m, a=alt: a, c) for c in candidates for alt in variants[value]]
        for c in candidates:
            if _squash(c) in haystack:
                return c
    # Mixed spellings of one name inside one quote: try one occurrence at a time.
    for value in present[:4]:
        for m in re.finditer(re.escape(value), quote, re.IGNORECASE):
            for alt in variants[value]:
                c = quote[:m.start()] + alt + quote[m.end():]
                if _squash(c) in haystack:
                    return c
    return quote


def classify_doc(doc: Document) -> str:
    """Return ``"automated"`` for bot/notification emails; ``"human"`` otherwise."""
    folder = str(doc.metadata.get("folder") or "")
    if folder == "inbox-automated":
        return "automated"
    sender = str(doc.metadata.get("from") or "")
    if _BOT_FROM.search(sender):
        return "automated"
    return "human"


def _normalize_predicate(pred: str) -> str | None:
    """Map to controlled vocabulary; return None if unrecognisable."""
    pred = pred.strip().lower()
    if pred in PREDICATES:
        return pred
    if _ATTR_RE.match(pred):
        return pred
    if pred in PREDICATE_SYNONYMS:
        return PREDICATE_SYNONYMS[pred]
    return None


def _normalize_subject(subject: str, predicate: str) -> str | None:
    """Return a cleaned subject or None if it looks like a code artefact."""
    subject = subject.strip()
    # Allow MR !284 / issue #284 if predicate is status/completed/proposed
    mr = _MR_RE.match(subject)
    if mr:
        _MR_OK = {"status", "completed", "proposed", "deadline", "blocked_by", "assigned_to", "requested"}
        if predicate in _MR_OK:
            kind = "MR" if subject.startswith("!") else "issue"
            return f"{kind} {subject}"
        return None
    if _NON_ENTITY_RE.match(subject):
        return None
    return subject


def _build_header(doc: Document, roster: Roster | None) -> str:
    """Render a compact header line for the LLM prompt."""
    meta = doc.metadata
    lines: list[str] = []
    if doc.kind == "email":
        if meta.get("from"):
            lines.append(f"From: {meta['from']}")
        if meta.get("to"):
            to_val = meta["to"]
            if isinstance(to_val, list):
                to_val = ", ".join(str(v) for v in to_val)
            lines.append(f"To: {to_val}")
        if meta.get("cc"):
            cc_val = meta["cc"]
            if isinstance(cc_val, list):
                cc_val = ", ".join(str(v) for v in cc_val if v)
            if cc_val:
                lines.append(f"Cc: {cc_val}")
        if meta.get("subject"):
            lines.append(f"Subject: {meta['subject']}")
        if meta.get("folder"):
            lines.append(f"Folder: {meta['folder']}")
    elif doc.kind in ("slack", "chat"):
        ch = meta.get("channel_name") or meta.get("channel") or ""
        if ch:
            lines.append(f"Channel: #{ch}")
    return "\n".join(lines)


def render_for_llm(doc: Document, roster: Roster | None = None, *, known_people: bool = True) -> str:
    """Build the text the LLM receives: optional header + cleaned body.

    Changes vs. raw document text:
    - Email and Slack headers are prepended so attribution is visible.
    - ``<@Uxxx>`` Slack mentions are replaced with names.
    - ``[ts=…]`` and ``(thread reply to …)`` clutter is stripped.
    - If a roster is supplied, a "Known people:" hint is appended.
    """
    header = _build_header(doc, roster)
    body = doc.text

    # Replace Slack user id mentions with names
    if roster:
        body = roster.render(body)

    # Strip [ts=…] and thread-reply noise
    body = _TS_NOISE.sub("", body)

    parts = []
    if header:
        parts.append(header)
    parts.append(body)

    if known_people and roster and roster.people:
        known = ", ".join(roster.people[:30])  # cap to avoid huge prompts
        parts.append(f"\nKnown people: {known}")

    return "\n".join(parts)


class ClaimExtractor:
    def __init__(self, llm: LLM, *, model: str = "nemotron", cache: DiskCache | None = None,
                 config: NormalizerConfig | None = None, roster: Roster | None = None) -> None:
        self.llm, self.model, self.cache, self.config = llm, model, cache, config
        self.roster = roster
        self.dropped: Counter[str] = Counter()
        self._lock = threading.Lock()

    def _raw_claims(self, doc: Document) -> list[dict[str, Any]]:
        doc_kind = classify_doc(doc)
        rendered = render_for_llm(doc, self.roster)
        key = cache_key(self.model, PROMPT_VERSION, doc.doc_date.isoformat() if doc.doc_date else "",
                        rendered, doc_kind)
        if self.cache and (hit := self.cache.get(key)) is not None:
            return hit
        prompt = SYSTEM_PROMPT_HUMAN if doc_kind == "human" else SYSTEM_PROMPT_AUTOMATED
        messages = [
            {"role": "system", "content": prompt.replace("{doc_date}", str(doc.doc_date))
             .replace("{predicates}", str(PREDICATES))},
            {"role": "user", "content": rendered},
        ]
        try:
            raw = parse_llm_json(self.llm.complete(messages, CLAIMS_SCHEMA))
        except ValueError:  # one repair retry
            messages.append({"role": "user", "content": 'Reply with ONLY valid JSON: {"claims": [...]}'})
            raw = parse_llm_json(self.llm.complete(messages, CLAIMS_SCHEMA))
        variants = getattr(self.llm, "restore_variants", lambda: {})()
        if variants:
            haystack = _squash(rendered)
            for c in raw:
                if isinstance(c.get("quote"), str):
                    c["quote"] = restore_quote(c["quote"], haystack, variants)
        if self.cache:
            self.cache.put(key, raw)
        return raw

    def extract(self, doc: Document) -> list[Claim]:
        if doc.doc_date is None:
            raise ValueError(f"{doc.doc_id}: document has no date; refusing to stamp with ingestion time")
        rendered = render_for_llm(doc, self.roster)
        haystack = _squash(rendered)
        claims = []
        replacements = set()
        for c in self._raw_claims(doc):
            if not all(c.get(k) for k in ("subject", "predicate", "object")):
                with self._lock:
                    self.dropped["missing_field"] += 1
                continue

            quote = str(c.get("quote") or "").strip()
            if not quote or _squash(quote) not in haystack:
                with self._lock:
                    self.dropped["quote"] += 1
                continue

            pred = _normalize_predicate(str(c["predicate"]))
            if pred is None:
                with self._lock:
                    self.dropped["predicate"] += 1
                continue

            subj = _normalize_subject(str(c["subject"]), pred)
            if subj is None:
                with self._lock:
                    self.dropped["non_entity"] += 1
                continue

            start = resolve(c.get("valid_from"), doc.doc_date, config=self.config)
            end = resolve(c.get("valid_to"), doc.doc_date, config=self.config)
            conf = float(c.get("confidence") or 1.0)
            if c.get("valid_from") and start.start is None:
                conf = min(conf, 0.4)
            predicate, obj = normalize_claim_value(pred, str(c["object"]))
            if predicate in DATED_PREDICATES and start.start is not None:
                replacements.add((_squash(subj), predicate))
            claims.append(Claim(
                subject=subj, predicate=predicate,
                object=obj,
                valid_from=start.start or (None if end.start else doc.doc_date),  # closing claim: start unknown
                valid_to=end.start if end.start else None,
                observed_at=doc.doc_date,
                doc_id=doc.doc_id, quote=quote,
                confidence=max(0.0, min(1.0, conf * min(start.confidence or 1, 1))),
            ))
        result = []
        for claim in claims:
            if (claim.predicate in DATED_PREDICATES and claim.valid_from is None and claim.valid_to is not None
                    and (_squash(claim.subject), claim.predicate) in replacements):
                # A same-document replacement already closes the previous P2 schedule.
                with self._lock:
                    self.dropped["redundant_closing"] += 1
                continue
            result.append(claim)
        return result

    @property
    def dropped_total(self) -> int:
        return sum(self.dropped.values())


def extract_entities(event: Event) -> list[Entity]:
    """Return a conservative set of capitalized names from event content (legacy heuristic)."""
    words = event.content.replace(",", " ").split()
    names = []
    for word in words:
        candidate = word.strip(".!?():;\"'")
        if candidate and candidate[0].isupper() and candidate not in {"The", "A", "I", "Met"}:
            names.append(Entity(name=candidate))
    return names
