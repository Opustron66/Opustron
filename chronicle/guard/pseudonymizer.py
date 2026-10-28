"""Reversible PII pseudonymisation.

Maps real values → ENTITY_N tokens before any external LLM call,
and restores them on the way back.

  mapping = PseudonymMapping()
  redacted, mapping = pseudonymize(text, mapping)
  # ... LLM call with redacted text ...
  restored = reidentify(llm_response, mapping)
"""

from __future__ import annotations

import os
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

# ---------------------------------------------------------------------------
# Stand-in names (CHRONICLE_PSEUDONYMS=surrogate)
# ---------------------------------------------------------------------------
# A model reasons better about "Jordan Okafor" than about "PERSON_1". Stand-ins
# are gender-neutral, are not ordinary English words (so restoring them cannot
# touch normal text), and never reuse a word that appears in the request.

_SURROGATE_TYPES = frozenset({"PERSON", "ORGANIZATION", "LOCATION"})

_FIRST_NAMES = (
    "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn", "Rowan", "Emerson",
    "Finley", "Hayden", "Kendall", "Logan", "Parker", "Reese", "Skyler", "Jamie", "Jesse",
    "Remy", "Shay", "Tatum", "Dakota", "Elliot", "Harley", "Jules", "Lennon", "Marlowe",
    "Oakley", "Peyton", "Sasha", "Sloane", "Teagan", "Arden", "Blair", "Cameron", "Emery",
    "Harper", "Jaden", "Micah", "Noel",
)
_LAST_NAMES = (
    "Okafor", "Lindqvist", "Varga", "Moreau", "Castellanos", "Nakashima", "Abernathy",
    "Delacroix", "Fairbanks", "Galloway", "Hendricks", "Iverson", "Jankowski", "Kowalczyk",
    "Lindgren", "Marchetti", "Novak", "Oyelaran", "Petrakis", "Quintero", "Rasmussen", "Szabo",
    "Thorsen", "Ueda", "Valdivia", "Whitlock", "Yilmaz", "Zielinski", "Bergstrom", "Calloway",
    "Dimitriou", "Esposito", "Grimaldi", "Halvorsen", "Ibarra", "Kaminski", "Ndiaye",
    "Ostrowski", "Pellegrini", "Sorensen",
)
_PLACE_NAMES = (
    "Alderbrook", "Brindlewood", "Corvane", "Dunmere", "Elmsworth", "Fallowmere", "Glenhollow",
    "Harrowgate", "Ivelton", "Marrowfield", "Northcliff", "Oakhurst", "Pemberly", "Quillfield",
    "Ravensworth", "Stonebridge", "Thornbury", "Underholt", "Vexford", "Westmere", "Yarrowby",
    "Zennorth", "Ashcombe", "Birchmoor", "Coldharbour", "Daleford", "Eastwick", "Foxleigh",
)
# Trailing words kept as-is, because they say what kind of thing it is without identifying it.
_GENERIC_TAIL = frozenset({
    "row", "depot", "street", "st", "road", "rd", "park", "site", "yard", "labs", "lab", "ltd",
    "inc", "group", "holdings", "bank", "tower", "point", "wharf", "bridge", "centre", "center",
    "hospital", "school", "college", "university", "station", "square", "hall", "works", "mill",
    "house", "court", "gardens", "lane", "way", "avenue", "place", "partners", "systems",
    "solutions", "technologies", "corp", "co", "llc", "plc", "project", "estate", "quay",
    "terrace", "plaza", "campus", "office", "warehouse",
})


def _style() -> str:
    value = os.environ.get("CHRONICLE_PSEUDONYMS", "").strip().lower()
    return "surrogate" if value in ("surrogate", "surrogates") else "token"


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
    _name_types: dict[str, str] = field(default_factory=dict)  # name key → entity type
    _name_spelling: dict[str, str] = field(default_factory=dict)  # name key → surface as detected
    # Stand-in mode: each name token gets one stand-in identity (first word, last word).
    style: str = field(default_factory=_style)
    _avoid: set[str] = field(default_factory=set)            # casefolded words in the request
    _identity: dict[str, tuple[str, str]] = field(default_factory=dict)  # token → (head, last)
    _key_display: dict[str, str] = field(default_factory=dict)  # name key → stand-in text
    # stand-in text → ("token", token) to restore the full name, or ("text", real) for a
    # first-name-only stand-in; ("", "") when two different originals share it.
    _restore: dict[str, tuple[str, str]] = field(default_factory=dict)
    _person_first: dict[str, str] = field(default_factory=dict)  # real first name → stand-in first
    _place_head: dict[str, str] = field(default_factory=dict)    # real head word → stand-in head
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def avoid(self, texts: list[str]) -> None:
        """Words a stand-in must never use: anything already in the request."""
        with self._lock:
            for text in texts:
                self._avoid.update(w.casefold() for w in re.findall(r"\w+", text))

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
                self._name_types.setdefault(key, entity_type)
                self._name_spelling.setdefault(key, surface)
                if head is not None and head not in self._forward:
                    self._forward[head] = token
                    self._name_keys[head] = token
                    self._name_types[head] = entity_type
                    self._aliases.add(head)
                if self.style == "surrogate" and entity_type in _SURROGATE_TYPES:
                    self._assign_surrogate(token, entity_type, key, surface, head)
            return token

    # -- stand-in names (called with the lock held) ----------------------------------------

    def _pick(self, pool: tuple[str, ...], taken: set[str]) -> str | None:
        for name in pool:
            folded = name.casefold()
            if folded not in self._avoid and folded not in taken:
                return name
        return None

    def _assign_surrogate(self, token: str, entity_type: str, key: str, surface: str,
                          head: str | None) -> None:
        words = surface.split()
        if token not in self._identity:
            used = {w.casefold() for pair in self._identity.values() for w in pair if w}
            if entity_type == "PERSON":
                real_first = words[0].casefold()
                first = self._person_first.get(real_first) or self._pick(_FIRST_NAMES, used)
                last = self._pick(_LAST_NAMES, used | ({first.casefold()} if first else set()))
                if first is None or last is None:
                    return  # pools exhausted: this name keeps its token
                self._person_first.setdefault(real_first, first)
                self._identity[token] = (first, last)
            else:
                # Look-alikes keep their likeness: "Camden Row" and "Camden Yard" become
                # "Alderbrook Row" and "Alderbrook Yard", so the model can still tell they are
                # related (disambiguation questions) without seeing the real name. Only when
                # the rest is generic; "Camden Logistics" vs "Camden Foods" get separate names.
                real_head = words[0].casefold()
                generic_tail = len(words) > 1 and all(w.casefold() in _GENERIC_TAIL for w in words[1:])
                place = (self._place_head.get(real_head) if generic_tail else None) or self._pick(_PLACE_NAMES, used)
                if place is None:
                    return
                if generic_tail:
                    self._place_head.setdefault(real_head, place)
                self._identity[token] = (place, "")
        first, last = self._identity[token]
        if entity_type == "PERSON":
            display = first if len(words) == 1 else f"{first} {last}"
        else:
            tail = words[1:] if all(w.casefold() in _GENERIC_TAIL for w in words[1:]) else []
            display = " ".join([first, *tail])
        self._key_display[key] = display
        if head is not None:
            self._key_display.setdefault(head, first)
        # A full stand-in restores its own original. Its first word alone ("Jordan",
        # "Alderbrook") restores to the real first word ("Dana", "Camden"), which every
        # entity sharing that stand-in word also shares.
        if display == first:
            targets = {first: ("token", token)}
        else:
            targets = {first: ("text", words[0]), display: ("token", token)}
        for text, target in targets.items():
            existing = self._restore.setdefault(text, target)
            if existing != target and self._resolve(existing) != self._resolve(target):
                self._restore[text] = ("", "")

    def _resolve(self, target: tuple[str, str]) -> str | None:
        kind, value = target
        if kind == "token":
            return self._reverse.get(value)
        return value if kind == "text" else None

    def display(self, text: str, token: str) -> str:
        """What the model sees for a name occurrence: its stand-in, or the token."""
        with self._lock:
            return self._key_display.get(_normalise(text), token)

    def surrogate_pattern(self) -> re.Pattern[str] | None:
        """Matches every restorable stand-in in model output, longest first."""
        with self._lock:
            names = sorted((s for s, (kind, _) in self._restore.items() if kind), key=len, reverse=True)
        if not names:
            return None
        return re.compile(r"(?<!\w)(?:" + "|".join(re.escape(n) for n in names) + r")(?!\w)")

    def original_for_surrogate(self, text: str) -> str | None:
        with self._lock:
            return self._resolve(self._restore.get(text, ("", "")))

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
        """One regex matching every registered name key, longest first, word-bounded.

        Names match in any case, so lowercase chat mentions ("dana", "camden's") stay hidden.
        The exception is a single-word organisation or place that is not a head-word alias:
        spaCy tags words like "Grace" as organisations, and matching those in any case would
        turn "grace period" into "ORG_1 period". Those match only as detected ("Grace").
        """
        with self._lock:
            keys = sorted(self._name_keys, key=len, reverse=True)
            exact = {
                k: self._name_spelling.get(k, k) for k in keys
                if len(k.split()) == 1 and k not in self._aliases
                and self._name_types.get(k) in ("ORGANIZATION", "LOCATION", "NRP")
            }
        if not keys:
            return None
        loose = [r"\s+".join(re.escape(w) for w in k.split()) for k in keys if k not in exact]
        strict = [re.escape(exact[k]) for k in keys if k in exact]
        alts = ([f"(?i:{'|'.join(loose)})"] if loose else []) + strict
        return re.compile(r"(?<!\w)(?:" + "|".join(alts) + r")(?!\w)")

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
    if mapping.style == "surrogate":
        mapping.avoid(texts)

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
    return mapping.display(text, token)


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
    """Replace ENTITY_N tokens (and stand-in names) in an LLM response with original values."""

    def replace(m: re.Match) -> str:  # type: ignore[type-arg]
        original = mapping.original_for(m.group())
        return original if original is not None else m.group()

    def replace_surrogate(m: re.Match) -> str:  # type: ignore[type-arg]
        original = mapping.original_for_surrogate(m.group())
        return original if original is not None else m.group()

    restored = _TOKEN_RE.sub(replace, text)
    pattern = mapping.surrogate_pattern()
    return pattern.sub(replace_surrogate, restored) if pattern is not None else restored
