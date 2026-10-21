"""Reversible PII pseudonymisation.

Maps real values → ENTITY_N tokens before any external LLM call,
and restores them on the way back.

  mapping = PseudonymMapping()
  redacted, mapping = pseudonymize(text, mapping)
  # ... LLM call with redacted text ...
  restored = reidentify(llm_response, mapping)
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field

from .pii_detector import GENERIC_TERMS, PiiMatch, detect

# ---------------------------------------------------------------------------
# Entity-type → token-prefix mapping
# ---------------------------------------------------------------------------

_PREFIX: dict[str, str] = {
    "PERSON": "PERSON",
    "ORGANIZATION": "ORG",
    "LOCATION": "LOC",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "US_SSN": "SSN",
    "CREDIT_CARD": "CARD",
    "IP_ADDRESS": "IP",
    "URL": "URL",
    "NRP": "NRP",
    "DATE_TIME": "DATE",
    "US_DRIVER_LICENSE": "DL",
    "US_PASSPORT": "PASSPORT",
    "US_ITIN": "ITIN",
    "MEDICAL_LICENSE": "MED",
}

_DEFAULT_PREFIX = "PII"


# Names, organisations and places: replaced wherever their text appears in the
# request, so one entity gets one token even where NER missed a mention. The
# rest (emails, phones, IDs, URLs) keep exact span replacement.
_NAME_TYPES = frozenset({"PERSON", "ORGANIZATION", "LOCATION", "NRP"})
_ALIAS_TYPES = frozenset({"ORGANIZATION", "LOCATION"})

_POSSESSIVE_RE = re.compile(r"['\u2019]s$", re.IGNORECASE)


def _surface(value: str) -> str:
    """Value as it should read when restored: trimmed, possessive dropped."""
    return _POSSESSIVE_RE.sub("", " ".join(value.split()))


def _normalise(value: str) -> str:
    """Lookup key: casefolded, possessive dropped, whitespace collapsed."""
    return _surface(value).casefold()


def _alias_head(entity_type: str, value: str) -> str | None:
    """'Camden Row' -> 'camden': the capitalised head word a multi-word ORG/LOC is
    often shortened to in chat. None when there is no safe head."""
    if entity_type not in _ALIAS_TYPES:
        return None
    words = value.split()
    if len(words) < 2:
        return None
    head = words[0]
    if not (head[:1].isupper() and head.isalpha() and len(head) >= 4):
        return None
    if head.casefold() in GENERIC_TERMS:
        return None
    return head.casefold()


@dataclass
class PseudonymMapping:
    """Thread-safe bidirectional map between real values and ENTITY_N tokens."""

    _forward: dict[str, str] = field(default_factory=dict)   # key    → token
    _reverse: dict[str, str] = field(default_factory=dict)   # token  → value
    _counters: dict[str, int] = field(default_factory=dict)  # prefix → count
    _name_keys: dict[str, str] = field(default_factory=dict)  # name key → token
    _aliases: set[str] = field(default_factory=set)          # head-word keys
    _surfaces: dict[str, dict[str, str]] = field(default_factory=dict)  # token → spellings seen
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def token_for(self, entity_type: str, value: str) -> str:
        """Return (and cache) the stable token for a given real value.

        Values are keyed case- and possessive-insensitively, so "Camden Row"
        and "camden row's" share a token. A multi-word ORG/LOC also claims its
        head word ("camden"), and reuses that word's token if it was seen alone first.
        """
        key = _normalise(value)
        surface = _surface(value)
        is_name = entity_type in _NAME_TYPES
        head = _alias_head(entity_type, surface) if is_name else None
        with self._lock:
            token = self._forward.get(key)
            if token is None and head is not None and head in self._forward and head not in self._aliases:
                # "camden" was registered on its own; "Camden Row" is the full name.
                token = self._forward[head]
                self._reverse[token] = surface
            if token is None:
                prefix = _PREFIX.get(entity_type, _DEFAULT_PREFIX)
                n = self._counters.get(prefix, 0) + 1
                self._counters[prefix] = n
                token = f"{prefix}_{n}"
                self._reverse[token] = surface
            self._forward[key] = token
            if is_name:
                self._name_keys[key] = token
                if head is not None and head not in self._forward:
                    self._forward[head] = token
                    self._name_keys[head] = token
                    self._aliases.add(head)
            return token

    def note_surface(self, token: str, text: str) -> None:
        """Record how a source text spelled a token's value ("camden", "Camden Row's")."""
        with self._lock:
            self._surfaces.setdefault(token, {}).setdefault(" ".join(text.split()).casefold(),
                                                            " ".join(text.split()))

    def surfaces(self) -> dict[str, list[str]]:
        """Restored value → the other spellings its token replaced in the request.

        ``reidentify`` always restores the full name, so a quote the model copied from
        "camden's crew" comes back as "Camden Row crew". Callers that check quotes
        against the source can try these spellings instead.
        """
        with self._lock:
            out = {}
            for token, seen in self._surfaces.items():
                value = self._reverse.get(token)
                if value is None:
                    continue
                others = [v for k, v in seen.items() if k != value.casefold()]
                if others:
                    out[value] = others
            return out

    def original_for(self, token: str) -> str | None:
        with self._lock:
            return self._reverse.get(token)

    def pii_types_seen(self) -> list[str]:
        with self._lock:
            return list({v.rsplit("_", 1)[0] for v in self._forward.values()})

    def name_pattern(self) -> re.Pattern[str] | None:
        """One regex matching every registered name key, longest first, word-bounded."""
        with self._lock:
            keys = sorted(self._name_keys, key=len, reverse=True)
        if not keys:
            return None
        alts = [r"\s+".join(re.escape(w) for w in k.split()) for k in keys]
        return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)", re.IGNORECASE)

    def name_token(self, text: str) -> str | None:
        with self._lock:
            return self._name_keys.get(_normalise(text))


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def pseudonymize_all(
    texts: list[str],
    mapping: PseudonymMapping | None = None,
    entities: list[list[PiiMatch]] | None = None,
) -> tuple[list[str], PseudonymMapping]:
    """Pseudonymise several texts that travel together (one LLM request).

    Pass 1 registers every detected value in reading order. Pass 2 replaces
    emails/phones/IDs by their spans, then every occurrence of every registered
    name in every text, so a name NER caught in one message is also hidden
    where it missed it in another.
    """
    if mapping is None:
        mapping = PseudonymMapping()
    if entities is None:
        entities = [detect(t) for t in texts]

    span_tokens: list[list[tuple[PiiMatch, str]]] = []
    for found in entities:
        ordered = sorted(found, key=lambda m: m.start)
        span_tokens.append([(m, mapping.token_for(m.entity_type, m.value)) for m in ordered])

    pattern = mapping.name_pattern()
    out: list[str] = []
    for text, pairs in zip(texts, span_tokens):
        result = text
        # Right-to-left so earlier offsets stay valid.
        for match, token in reversed(pairs):
            if match.entity_type not in _NAME_TYPES:
                result = result[: match.start] + token + result[match.end :]
        if pattern is not None:
            result = pattern.sub(lambda m: _swap(mapping, m.group()), result)
        out.append(result)
    return out, mapping


def _swap(mapping: PseudonymMapping, text: str) -> str:
    token = mapping.name_token(text)
    if token is None:
        return text
    mapping.note_surface(token, text)
    return token


def pseudonymize(
    text: str,
    mapping: PseudonymMapping | None = None,
    entities: list[PiiMatch] | None = None,
) -> tuple[str, PseudonymMapping]:
    """Replace PII with ENTITY_N tokens.

    Returns (redacted_text, mapping). Pass an existing mapping to reuse tokens
    across multiple texts in the same session.
    """
    [redacted], mapping = pseudonymize_all(
        [text], mapping, entities=None if entities is None else [entities]
    )
    return redacted, mapping


_TOKEN_RE = re.compile(
    r"\b(?:PERSON|ORG|LOC|EMAIL|PHONE|SSN|CARD|IP|URL|NRP|DATE|DL|PASSPORT|ITIN|MED|PII)_\d+\b"
)


def reidentify(text: str, mapping: PseudonymMapping) -> str:
    """Replace ENTITY_N tokens in LLM response with original values."""

    def replace(m: re.Match) -> str:  # type: ignore[type-arg]
        original = mapping.original_for(m.group())
        return original if original is not None else m.group()

    return _TOKEN_RE.sub(replace, text)
