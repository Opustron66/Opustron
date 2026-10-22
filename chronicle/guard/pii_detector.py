"""PII detection: regex patterns + Presidio NER.

Tier 1 (always available): regex for emails, phones, SSNs, cards, IPs, URLs.
Tier 2 (Presidio + spaCy en_core_web_sm, installed by default): names,
organisations and places. If it can't load, a warning is logged once and only
Tier 1 runs; ``ner_available()`` reports which.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns (Tier 1)
# ---------------------------------------------------------------------------

_PATTERNS: dict[str, re.Pattern[str]] = {
    "EMAIL_ADDRESS": re.compile(
        r"\b[\w.+\-]+@[\w\-]+\.[\w.\-]+\b", re.IGNORECASE
    ),
    "PHONE_NUMBER": re.compile(
        r"""(?<!\d)(?:\+?1[\s.\-]?)?"""
        r"""(?:\(?\d{3}\)?[\s.\-]?)"""
        r"""\d{3}[\s.\-]?\d{4}(?!\d)"""
    ),
    "US_SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(
        r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b"
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
    ),
    "URL": re.compile(r"https?://[\w\-._~:/?#\[\]@!$&'()*+,;=%]+"),
}


@dataclass(slots=True)
class PiiMatch:
    entity_type: str
    value: str
    start: int
    end: int


def _regex_detect(text: str) -> list[PiiMatch]:
    matches: list[PiiMatch] = []
    for entity_type, pattern in _PATTERNS.items():
        for m in pattern.finditer(text):
            matches.append(PiiMatch(entity_type, m.group(), m.start(), m.end()))
    return matches


# ---------------------------------------------------------------------------
# Presidio tier (Tier 2) — imported lazily so the package works without it
# ---------------------------------------------------------------------------

_presidio_analyzer = None
_presidio_load_failed = False


def _get_presidio_analyzer():
    global _presidio_analyzer, _presidio_load_failed
    if _presidio_analyzer is not None or _presidio_load_failed:
        return _presidio_analyzer
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        _presidio_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
    except Exception as exc:
        _presidio_load_failed = True
        logger.warning(
            "Name detection is OFF (Presidio/spaCy unavailable: %s). Only emails, phones, IDs "
            "and URLs will be pseudonymised. Run `uv sync` to install it.",
            exc,
        )
    return _presidio_analyzer


def ner_available() -> bool:
    """True when names, organisations and places are being detected."""
    return _get_presidio_analyzer() is not None


# DATE_TIME is deliberately absent: dates are what Chronicle reasons about
# ("who owned payments on 3 May?"), and a model shown DATE_1 can't order facts.
_PRESIDIO_ENTITY_TYPES = {
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "NRP",
    "MEDICAL_LICENSE",
    "URL",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "US_ITIN",
}


# spaCy tags these as entities in site-ops text ("Tower crane", "ETA"). They are
# not identifying, and a model shown ORG_3 for "ETA" loses the question's meaning.
GENERIC_TERMS = frozenset({"tower", "eta", "row", "depot", "site", "crane", "gate", "board"})
_ACRONYM_RE = re.compile(r"[A-Z]{2,3}")

# Same convention as llm_client's env switches.
_FALSY = ("0", "false", "no", "off")
_names_off_warned = False


def names_redacted() -> bool:
    """False when CHRONICLE_REDACT_NAMES turns name detection off (benchmark runs only)."""
    global _names_off_warned
    if os.environ.get("CHRONICLE_REDACT_NAMES", "1").strip().lower() not in _FALSY:
        return True
    if not _names_off_warned:
        _names_off_warned = True
        logger.warning(
            "Name redaction disabled by CHRONICLE_REDACT_NAMES: names, organisations and places "
            "reach the LLM as-is. Emails, phones, IDs and URLs are still pseudonymised."
        )
    return False


# Kept by CHRONICLE_REDACT_NAMES=person: people stay masked; organisations and places (which in a
# site-operations corpus are mostly project and site names) reach the model as written.
_PERSON_ONLY_DROPS = frozenset({"ORGANIZATION", "LOCATION", "NRP"})


def person_only() -> bool:
    """True when CHRONICLE_REDACT_NAMES=person: pseudonymise people, not organisations or places."""
    return os.environ.get("CHRONICLE_REDACT_NAMES", "").strip().lower() == "person"


def _is_generic(entity_type: str, value: str) -> bool:
    # The word list applies to every type: spaCy also tags a bare "Tower" as PERSON.
    value = value.strip()
    if value.casefold() in GENERIC_TERMS:
        return True
    return entity_type in ("ORGANIZATION", "LOCATION") and bool(_ACRONYM_RE.fullmatch(value))


_NAME_TYPES = frozenset({"PERSON", "ORGANIZATION", "LOCATION", "NRP"})
# spaCy runs a name into the text after it ("Rohan Dasgupta: +1 jordan", JSON, code).
_NAME_CUT = re.compile(r"[:\n(=\"{}\[\]]")
_DIGIT = re.compile(r"\d")


def _clean_name(entity_type: str, start: int, end: int, value: str) -> tuple[int, int, str] | None:
    """Trim a name span at the first separator and drop spans that are not names.

    spaCy tags values as names in this corpus ("0.71¢", "300ms", "Q4", "KR3", "v1→v2"). Pass two
    of pseudonymisation replaces a registered name everywhere in the request, so one such span
    hides that value from every message. Names here never contain digits.
    """
    if entity_type not in _NAME_TYPES:
        return start, end, value
    cut = _NAME_CUT.search(value)
    if cut:
        value = value[: cut.start()]
    trimmed = value.rstrip(" .,;-")
    value = trimmed.lstrip(" .,;-")
    start += len(trimmed) - len(value)
    end = start + len(value)
    if len(value) < 2 or _DIGIT.search(value) or not any(ch.isalpha() for ch in value):
        return None
    return start, end, value


def _presidio_detect(text: str) -> list[PiiMatch]:
    if not names_redacted():
        return []
    analyzer = _get_presidio_analyzer()
    if analyzer is None:
        return []
    results = analyzer.analyze(
        text=text,
        entities=list(_PRESIDIO_ENTITY_TYPES),
        language="en",
    )
    matches = []
    for r in results:
        if r.score < 0.6 or (person_only() and r.entity_type in _PERSON_ONLY_DROPS):
            continue
        cleaned = _clean_name(r.entity_type, r.start, r.end, text[r.start : r.end])
        if cleaned is None or _is_generic(r.entity_type, cleaned[2]):
            continue
        matches.append(PiiMatch(r.entity_type, cleaned[2], cleaned[0], cleaned[1]))
    return matches


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(text: str) -> list[PiiMatch]:
    """Return all PII matches, sorted by start position, deduplicated."""
    matches = _regex_detect(text) + _presidio_detect(text)
    # Sort by start, then deduplicate overlapping spans (prefer longer match)
    matches.sort(key=lambda m: (m.start, -(m.end - m.start)))
    deduped: list[PiiMatch] = []
    last_end = -1
    for m in matches:
        if m.start >= last_end:
            deduped.append(m)
            last_end = m.end
    return deduped


def contains_pii(text: str) -> bool:
    return bool(detect(text))


def contains_email(text: str) -> bool:
    return bool(_PATTERNS["EMAIL_ADDRESS"].search(text))
