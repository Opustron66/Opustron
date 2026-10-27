"""Stand-in names (CHRONICLE_PSEUDONYMS=surrogate) and single-word over-masking."""

import re
from types import SimpleNamespace

import pytest

from chronicle.guard import egress_logger, llm_client
from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.llm_client import PLACEHOLDER_NOTE, LLMClient
from chronicle.guard.pii_detector import PiiMatch
from chronicle.guard.pseudonymizer import (
    _FIRST_NAMES,
    PseudonymMapping,
    pseudonymize_all,
    reidentify,
)

TOKEN = re.compile(r"\b(?:PERSON|ORG|LOC)_\d+\b")


def match(text, value, entity_type="PERSON", start=0):
    i = text.index(value, start)
    return PiiMatch(entity_type, value, i, i + len(value))


def run(texts, entities, style="surrogate"):
    return pseudonymize_all(texts, PseudonymMapping(style=style), entities=entities)


TAKEOVER = "Effective 15 May, Dana Whitfield takes over payments from Alice Tan. Mail dana@corp.io."


def takeover_entities(text=TAKEOVER):
    return [[match(text, "Dana Whitfield"), match(text, "Alice Tan"),
             match(text, "dana@corp.io", "EMAIL_ADDRESS")]]


def test_default_style_is_tokens(monkeypatch):
    monkeypatch.delenv("CHRONICLE_PSEUDONYMS", raising=False)
    [out], _ = pseudonymize_all([TAKEOVER], entities=takeover_entities())
    assert out == "Effective 15 May, PERSON_1 takes over payments from PERSON_2. Mail EMAIL_1."


def test_env_switches_on_stand_ins(monkeypatch):
    monkeypatch.setenv("CHRONICLE_PSEUDONYMS", "surrogate")
    assert PseudonymMapping().style == "surrogate"


def test_people_get_realistic_names_and_other_pii_keeps_tokens():
    [out], _ = run([TAKEOVER], takeover_entities())
    assert "Dana" not in out and "Alice" not in out and "dana@corp.io" not in out
    assert not TOKEN.search(out)
    assert "EMAIL_1" in out
    assert "15 May" in out
    people = re.findall(r"from (\w+ \w+)\.|May, (\w+ \w+) takes", out)
    assert len([p for pair in people for p in pair if p]) == 2


def test_round_trip_restores_full_names_first_names_and_tokens():
    text = TAKEOVER + " Dana confirmed."
    entities = takeover_entities(text)
    entities[0].append(match(text, "Dana", start=text.index("Dana confirmed")))
    [out], mapping = run([text], entities)
    stand_in = out.split("May, ")[1].split(" takes")[0]
    first = stand_in.split()[0]
    assert f"{first} confirmed." in out  # the bare first name shares the stand-in first name

    reply = f"{stand_in} owns payments; {first} confirmed. Contact EMAIL_1."
    assert reidentify(reply, mapping) == "Dana Whitfield owns payments; Dana confirmed. Contact dana@corp.io."


def test_stand_ins_never_use_a_word_from_the_request():
    taken = " ".join(_FIRST_NAMES[:5])
    text = f"{taken} are colleagues. Dana Whitfield joined."
    [out], mapping = run([text], [[match(text, "Dana Whitfield")]])
    stand_in = out.split(". ")[1].removesuffix(" joined.")
    assert stand_in.split()[0] not in _FIRST_NAMES[:5]
    # A real name from the request that the reply repeats is left alone.
    assert reidentify(f"{_FIRST_NAMES[0]} said hi to {stand_in}.", mapping) == f"{_FIRST_NAMES[0]} said hi to Dana Whitfield."


def test_places_keep_generic_words_and_their_short_form():
    text = "Ridgeway Depot closeout is late; the ridgeway register shows 14."
    [out], mapping = run([text], [[match(text, "Ridgeway Depot", "LOCATION")]])
    place = out.split(" Depot")[0]
    assert out == f"{place} Depot closeout is late; the {place} register shows 14."
    assert reidentify(f"{place} Depot is late.", mapping) == "Ridgeway Depot is late."


def test_same_request_gives_same_stand_ins():
    first, _ = run([TAKEOVER], takeover_entities())
    again, _ = run([TAKEOVER], takeover_entities())
    assert first == again  # stable text keeps the response cache warm


def test_running_out_of_stand_ins_falls_back_to_tokens():
    people = [f"Zed{chr(65 + i // 26)}{chr(65 + i % 26)} Quorvax" for i in range(len(_FIRST_NAMES) + 3)]
    text = ", ".join(people)
    entities = [[match(text, p) for p in people]]
    [out], mapping = run([text], entities)
    assert "Quorvax" not in out
    assert TOKEN.search(out)  # the overflow keeps tokens
    assert reidentify(out, mapping) == text


def test_no_placeholder_note_with_stand_ins(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONICLE_PSEUDONYMS", "surrogate")
    monkeypatch.setattr(llm_client, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(egress_logger, "_default_logger", EgressLogger(tmp_path / "egress.log"))
    sent = []

    def transport(**kwargs):
        sent.append(kwargs["messages"])
        stand_in = kwargs["messages"][-1]["content"].split("May, ")[1].split(" takes")[0]
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=f"{stand_in} owns payments."),
                                     finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=5, completion_tokens=3),
        )

    reply = LLMClient(api_key="t", use_cache=False, transport=transport).complete(
        [{"role": "user", "content": "Effective 15 May, Dana Whitfield takes over payments."}]
    )
    assert all(PLACEHOLDER_NOTE not in m["content"] for m in sent[0])
    assert "Dana Whitfield" not in sent[0][-1]["content"]
    assert reply == "Dana Whitfield owns payments."


@pytest.mark.parametrize("style", ["token", "surrogate"])
def test_single_word_organisation_does_not_mask_the_lowercase_word(style):
    text = "Grace signed the lease. The grace period ends 1 June."
    [out], _ = run([text], [[match(text, "Grace", "ORGANIZATION")]], style=style)
    assert "The grace period ends 1 June." in out
    assert not out.startswith("Grace")


def test_single_word_person_is_still_masked_in_lowercase_chat():
    text = "Dana approved it. ok thanks dana"
    [out], _ = run([text], [[match(text, "Dana")]], style="token")
    assert out == "PERSON_1 approved it. ok thanks PERSON_1"


def test_look_alike_places_share_a_stand_in_word_but_restore_separately():
    text = "Camden Row pour moved; Camden Yard is unaffected. Camden Logistics and Camden Foods bid."
    names = ["Camden Row", "Camden Yard", "Camden Logistics", "Camden Foods"]
    [out], mapping = run([text], [[match(text, n, "LOCATION") for n in names]])
    row, yard = out.split(" pour")[0], out.split("; ")[1].split(" is")[0]
    assert row.split()[0] == yard.split()[0] and row.endswith("Row") and yard.endswith("Yard")
    bidders = out.split("unaffected. ")[1].removesuffix(" bid.").split(" and ")
    assert len(set(bidders)) == 2 and row.split()[0] not in bidders
    assert reidentify(f"{yard} is fine, {row} moved; {bidders[1]} won.", mapping) == \
        "Camden Yard is fine, Camden Row moved; Camden Foods won."


def test_shared_head_alone_restores_to_the_real_head():
    text = "Camden Row and Camden Yard both slipped."
    [out], mapping = run([text], [[match(text, "Camden Row", "LOCATION"), match(text, "Camden Yard", "LOCATION")]])
    head = out.split()[0]
    assert reidentify(f"Both {head} sites slipped.", mapping) == "Both Camden sites slipped."
