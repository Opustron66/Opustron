from chronicle.guard.privacy_router import PrivacyRouter


def test_route_clean_text():
    router = PrivacyRouter()
    assert router.route("The meeting is at 9am") == "external"


def test_route_pii_text():
    router = PrivacyRouter()
    assert router.route("Email alice@example.com") == "local"


def test_redact_and_restore_roundtrip():
    router = PrivacyRouter()
    original = "Please contact alice@corp.com for the invoice"
    redacted, mapping = router.redact(original)
    assert "alice@corp.com" not in redacted
    restored = router.restore(redacted, mapping)
    assert restored == original


def test_redact_messages():
    router = PrivacyRouter()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "My email is test@example.com"},
    ]
    redacted, mapping = router.redact_messages(messages)
    assert "test@example.com" not in redacted[1]["content"]
    assert redacted[0]["content"] == messages[0]["content"]


def test_shared_mapping_across_messages():
    router = PrivacyRouter()
    messages = [
        {"role": "user", "content": "alice@example.com"},
        {"role": "user", "content": "Contact alice@example.com again"},
    ]
    redacted, mapping = router.redact_messages(messages)
    # Both should use the same EMAIL_1 token
    assert "EMAIL_1" in redacted[0]["content"]
    assert "EMAIL_1" in redacted[1]["content"]


def _fake_ner(monkeypatch, phrases):
    """Stand-in for spaCy that finds only the given exact phrases, like a patchy NER."""
    import re

    from chronicle.guard import pii_detector
    from chronicle.guard.pii_detector import PiiMatch

    def detect(text):
        return [
            PiiMatch(etype, m.group(), m.start(), m.end())
            for phrase, etype in phrases.items()
            for m in re.finditer(re.escape(phrase), text)
        ]

    monkeypatch.setattr(pii_detector, "_presidio_detect", detect)


def test_entity_gets_one_token_across_messages(monkeypatch):
    # NER catches the full name in the question but not the lowercase chat mentions.
    _fake_ner(monkeypatch, {"Camden Row": "LOCATION", "Ridgeway Depot": "ORGANIZATION"})
    router = PrivacyRouter()
    messages = [
        {"role": "user", "content": "What is the Camden Row budget contingency and the Ridgeway Depot count?"},
        {"role": "user", "content": "camden's carrying 6% contingency. the ridgeway closeout register shows 14."},
    ]
    redacted, mapping = router.redact_messages(messages)
    assert redacted[0]["content"] == "What is the LOC_1 budget contingency and the ORG_1 count?"
    assert redacted[1]["content"] == "LOC_1's carrying 6% contingency. the ORG_1 closeout register shows 14."
    restored = [router.restore(m["content"], mapping) for m in redacted]
    assert "Camden Row" in restored[0] and "Ridgeway Depot" in restored[0]
    assert restored[1].startswith("Camden Row's carrying")


def test_name_found_only_in_a_later_message_is_hidden_in_earlier_ones(monkeypatch):
    _fake_ner(monkeypatch, {"Dana Whitfield": "PERSON"})
    router = PrivacyRouter()
    messages = [
        {"role": "user", "content": "dana whitfield owns payments"},
        {"role": "user", "content": "Ask Dana Whitfield."},
    ]
    redacted, _ = router.redact_messages(messages)
    assert [m["content"] for m in redacted] == ["PERSON_1 owns payments", "Ask PERSON_1."]


def test_redact_matches_redact_messages_for_one_text(monkeypatch):
    _fake_ner(monkeypatch, {"Camden Row": "LOCATION"})
    router = PrivacyRouter()
    text = "Camden Row and camden, mail a@b.io"
    single, _ = router.redact(text)
    [msg], _ = router.redact_messages([{"role": "user", "content": text}])
    assert single == msg["content"] == "LOC_1 and LOC_1, mail EMAIL_1"
