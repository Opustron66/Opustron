"""Real Presidio + spaCy name detection (no fakes): names leave as tokens, dates don't."""

import logging
import sys
from types import SimpleNamespace

import pytest

from chronicle.guard import egress_logger, llm_client, pii_detector
from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.llm_client import LLMClient
from chronicle.guard.pii_detector import detect, ner_available
from chronicle.guard.pseudonymizer import pseudonymize, reidentify
from chronicle.integrations.tavily import PrivacyBlocked, TavilyClient

TAKEOVER = "Effective today, Dana Whitfield takes over payments from Alice Tan."


def test_name_detection_is_installed():
    # Fails CI (rather than silently sending names) if spaCy's model is missing.
    assert ner_available()


def test_full_names_are_detected():
    people = {m.value for m in detect(TAKEOVER) if m.entity_type == "PERSON"}
    assert people == {"Dana Whitfield", "Alice Tan"}


@pytest.mark.parametrize("text", ["due next Friday, 12 May 2026", "Who owned payments on 3 May?", "The meeting is at 9am tomorrow"])
def test_dates_are_never_pseudonymised(text):
    redacted, _ = pseudonymize(text)
    assert redacted == text


def test_names_round_trip_and_dates_survive():
    redacted, mapping = pseudonymize(TAKEOVER)
    assert redacted == "Effective today, PERSON_1 takes over payments from PERSON_2."
    assert reidentify(redacted, mapping) == TAKEOVER


def test_names_never_reach_the_model(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_client, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(egress_logger, "_default_logger", EgressLogger(tmp_path / "egress.log"))
    sent = []

    def transport(**kwargs):
        sent.append(kwargs["messages"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="PERSON_1 now owns payments."))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )

    client = LLMClient(api_key="test", use_cache=False, transport=transport)
    reply = client.complete([{"role": "user", "content": TAKEOVER}])

    outgoing = sent[0][0]["content"]
    assert "Dana Whitfield" not in outgoing and "Alice Tan" not in outgoing
    assert reply == "Dana Whitfield now owns payments."
    [entry] = egress_logger._default_logger.tail()
    assert "PERSON" in entry["pii_types"]


def test_tavily_refuses_a_query_naming_a_person():
    with pytest.raises(PrivacyBlocked) as exc:
        TavilyClient("k", transport=lambda *a: b"{}").search("Alice Tan new job")
    assert "PERSON" in exc.value.pii_types


def test_missing_model_warns_once_and_falls_back(monkeypatch, caplog):
    monkeypatch.setattr(pii_detector, "_presidio_analyzer", None)
    monkeypatch.setattr(pii_detector, "_presidio_load_failed", False)
    monkeypatch.setitem(sys.modules, "presidio_analyzer", None)

    with caplog.at_level(logging.WARNING, logger="chronicle.guard.pii_detector"):
        assert not ner_available()
        assert {m.entity_type for m in detect("mail bob@corp.io")} == {"EMAIL_ADDRESS"}
        detect("again")
    assert sum("Name detection is OFF" in r.message for r in caplog.records) == 1


def test_generic_site_words_are_not_redacted():
    text = "The Tower crane ETA slipped; Tower is booked and the steel ETA is 11 August."
    redacted, _ = pseudonymize(text)
    assert redacted == text


def test_multi_word_place_and_its_short_form_share_a_token():
    redacted, mapping = pseudonymize(
        "Ridgeway Depot closeout is late; the ridgeway closeout register shows 14."
    )
    assert redacted == "ORG_1 closeout is late; the ORG_1 closeout register shows 14."
    assert reidentify(redacted, mapping).startswith("Ridgeway Depot closeout")


def test_redact_names_switch_keeps_names_but_not_emails(monkeypatch, caplog):
    monkeypatch.setenv("CHRONICLE_REDACT_NAMES", "off")
    monkeypatch.setattr(pii_detector, "_names_off_warned", False)
    with caplog.at_level(logging.WARNING, logger="chronicle.guard.pii_detector"):
        redacted, _ = pseudonymize(TAKEOVER + " Mail dana@corp.com.")
        pseudonymize(TAKEOVER)
    assert redacted == TAKEOVER + " Mail EMAIL_1."
    assert sum("CHRONICLE_REDACT_NAMES" in r.message for r in caplog.records) == 1


@pytest.mark.parametrize("value", ["", "1", "on", "yes"])
def test_redact_names_is_on_unless_switched_off(monkeypatch, value):
    monkeypatch.setenv("CHRONICLE_REDACT_NAMES", value)
    redacted, _ = pseudonymize(TAKEOVER)
    assert "Dana Whitfield" not in redacted


def test_person_only_mode_masks_people_but_not_places(monkeypatch):
    monkeypatch.setenv("CHRONICLE_REDACT_NAMES", "person")
    redacted, _ = pseudonymize("Dana Whitfield moved the Ridgeway Depot closeout.")
    assert "Dana Whitfield" not in redacted and "PERSON_1" in redacted
    assert "Ridgeway Depot" in redacted


@pytest.mark.parametrize("text, kept", [
    ("Peak was 0.71¢ two weeks ago.", "0.71¢"),
    ("The KR3 framing for Q4 is fine.", "KR3 framing for Q4"),
    ("p95 is 300ms after the v1→v2 cutover.", "300ms"),
])
def test_values_spacy_tags_as_names_are_not_masked(text, kept):
    redacted, _ = pseudonymize(text)
    assert kept in redacted


def test_name_spans_are_cut_at_speaker_separators():
    from chronicle.guard.pii_detector import _clean_name
    assert _clean_name("PERSON", 0, 25, "Rohan Dasgupta: +1 jordan") == (0, 14, "Rohan Dasgupta")
    assert _clean_name("ORGANIZATION", 5, 10, "Q4 KR") is None
    assert _clean_name("EMAIL_ADDRESS", 0, 9, "a@b.co x1") == (0, 9, "a@b.co x1")


# Regressions from benchmark run 1 (corpus A): masking bugs that garbled the answer prompt.

def test_prompt_labels_are_never_names():
    redacted, _ = pseudonymize("EVIDENCE:\nAlice Tan owns payments.\n\nQUESTION: Who owns payments?")
    assert "QUESTION: Who owns payments?" in redacted
    assert redacted.startswith("EVIDENCE:")


def test_all_caps_words_are_not_people():
    assert not [m for m in detect("REVIEW NOTES from the WAVE sync") if m.entity_type == "PERSON"]


def test_project_codenames_keep_their_prefix_and_never_claim_project():
    redacted, mapping = pseudonymize("Project Beacon shipped. Who leads Project Beacon? The project slipped.")
    assert "Project" in redacted and "The project slipped." in redacted
    assert "project" not in mapping._aliases


def test_lists_of_names_split_into_separate_entities():
    found = [m.value for m in detect("After Alex Chen and Sam Ortiz negotiated it, the RFC changed.")]
    assert "Alex Chen and Sam Ortiz" not in found
    assert not any("/" in v for v in [m.value for m in detect("see src/Atlas / Beacon / Compass/stores")])
