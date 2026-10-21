from chronicle.guard.pii_detector import PiiMatch
from chronicle.guard.pseudonymizer import (
    PseudonymMapping,
    pseudonymize,
    reidentify,
)


def test_email_is_redacted():
    redacted, _ = pseudonymize("Contact a@example.com")
    assert "a@example.com" not in redacted
    assert "EMAIL_1" in redacted


def test_same_value_gets_same_token():
    mapping = PseudonymMapping()
    text = "alice@example.com and alice@example.com again"
    redacted, mapping = pseudonymize(text, mapping)
    assert redacted.count("EMAIL_1") == 2


def test_different_values_get_different_tokens():
    mapping = PseudonymMapping()
    t1, mapping = pseudonymize("alice@example.com", mapping)
    t2, mapping = pseudonymize("bob@example.com", mapping)
    assert "EMAIL_1" in t1
    assert "EMAIL_2" in t2


def test_reidentify_restores_original():
    original = "Contact alice@example.com for help"
    redacted, mapping = pseudonymize(original)
    restored = reidentify(redacted, mapping)
    assert restored == original


def test_mapping_shared_across_texts():
    mapping = PseudonymMapping()
    _, mapping = pseudonymize("Call 555-867-5309", mapping)
    _, mapping = pseudonymize("Again: 555-867-5309", mapping)
    # Same phone should map to same token
    tokens = list(mapping._forward.values())
    assert len(set(tokens)) == 1


def test_no_pii_text_unchanged():
    text = "The quick brown fox jumps over the lazy dog."
    redacted, mapping = pseudonymize(text)
    assert redacted == text


def test_multiple_pii_types():
    text = "Alice can be reached at alice@corp.com or +1-800-555-0199"
    redacted, mapping = pseudonymize(text)
    assert "alice@corp.com" not in redacted
    assert "+1-800-555-0199" not in redacted
    assert len(mapping.pii_types_seen()) >= 1


def test_reidentify_unknown_token_unchanged():
    mapping = PseudonymMapping()
    result = reidentify("Hello PERSON_99 world", mapping)
    assert result == "Hello PERSON_99 world"


def test_mentions_differing_in_case_and_possessive_share_a_token():
    mapping = PseudonymMapping()
    a = mapping.token_for("LOCATION", "Camden Row")
    assert mapping.token_for("LOCATION", "camden row's") == a
    assert mapping.token_for("LOCATION", "CAMDEN  ROW") == a
    assert mapping.original_for(a) == "Camden Row"


def test_multi_word_place_claims_its_head_word():
    mapping = PseudonymMapping()
    a = mapping.token_for("LOCATION", "Camden Row")
    assert mapping.token_for("LOCATION", "camden") == a
    b = mapping.token_for("ORGANIZATION", "Ridgeway Depot")
    assert mapping.token_for("ORGANIZATION", "Ridgeway") == b
    assert a != b


def test_head_word_seen_first_is_merged_with_full_name():
    mapping = PseudonymMapping()
    a = mapping.token_for("LOCATION", "camden")
    assert mapping.token_for("LOCATION", "Camden Row") == a
    assert mapping.original_for(a) == "Camden Row"


def test_no_alias_for_short_generic_or_person_heads():
    mapping = PseudonymMapping()
    mapping.token_for("ORGANIZATION", "Site Office")    # generic head
    mapping.token_for("LOCATION", "Bay Road")           # head under 4 letters
    mapping.token_for("PERSON", "Dana Whitfield")       # people don't get head aliases
    assert {"site", "bay", "dana"}.isdisjoint(mapping._forward)


def test_given_entities_are_replaced_everywhere_in_the_text():
    text = "Camden Row is late. Everyone on camden row knows; camden's budget is tight."
    redacted, mapping = pseudonymize(text, entities=[PiiMatch("LOCATION", "Camden Row", 0, 10)])
    assert redacted == "LOC_1 is late. Everyone on LOC_1 knows; LOC_1's budget is tight."
    assert reidentify(redacted, mapping) == (
        "Camden Row is late. Everyone on Camden Row knows; Camden Row's budget is tight."
    )


def test_names_inside_emails_are_left_to_the_email_token():
    text = "Dana wrote from dana@corp.com"
    redacted, _ = pseudonymize(
        text,
        entities=[PiiMatch("PERSON", "Dana", 0, 4), PiiMatch("EMAIL_ADDRESS", "dana@corp.com", 16, 29)],
    )
    assert redacted == "PERSON_1 wrote from EMAIL_1"
