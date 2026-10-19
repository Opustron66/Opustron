from chronicle.memory.supersession import (
    SlotMember,
    normalize_predicate,
    resolve_slot,
    slot_for,
)


def member(fact_id, value, start, *, end=None, observed=None, seq=0):
    return SlotMember(fact_id, value, start, end, "stated", observed or start, seq)


def test_owns_competes_per_object_and_status_per_subject():
    assert slot_for("alice", "owns", "payments") == ("owns|obj|payments", "alice")
    assert slot_for("migration", "status", "blocked") == ("status|subj|migration", "blocked")
    assert slot_for("alice", "works_on", "atlas") == (None, None)


def test_normalize_predicate():
    assert normalize_predicate(" On-Call ") == "on_call"
    assert normalize_predicate("reports to") == "reports_to"


def test_handover_closes_previous_value():
    out = resolve_slot([member("a", "alice", "04-16", seq=1), member("d", "dana", "05-12", seq=2)])
    assert out["a"].valid_to == "05-12" and out["a"].superseded_by == "d" and out["a"].end_reason == "superseded"
    assert out["d"].valid_to is None and out["d"].superseded_by is None


def test_result_does_not_depend_on_order():
    members = [member("a", "alice", "01"), member("b", "bob", "03"), member("c", "carol", "02")]
    forward = resolve_slot(members)
    assert resolve_slot(list(reversed(members))) == forward
    assert forward["a"].superseded_by == "c" and forward["c"].superseded_by == "b"


def test_stated_end_before_successor_wins():
    out = resolve_slot([member("a", "alice", "01", end="02"), member("b", "bob", "05")])
    assert out["a"].valid_to == "02" and out["a"].end_reason == "stated" and out["a"].superseded_by is None


def test_same_start_later_statement_wins():
    out = resolve_slot([
        member("a", "alice", "05", observed="05", seq=1),
        member("b", "bob", "05", observed="06", seq=2),
    ])
    assert out["a"].valid_to == "05" and out["a"].superseded_by == "b"
    assert out["b"].valid_to is None


def test_unknown_start_is_never_superseded():
    out = resolve_slot([member("a", "alice", None, end="05"), member("c", "carol", "03")])
    assert out["a"].valid_to == "05" and out["a"].superseded_by is None


def test_same_value_does_not_supersede_itself():
    out = resolve_slot([member("a1", "alice", "01"), member("a2", "alice", "06")])
    assert out["a1"].valid_to is None
