"""Tests for chronicle.ingest.reconcile."""

from datetime import date

from chronicle.ingest.reconcile import ReconcileIndex
from chronicle.schema import Claim


def _claim(subject, predicate, obj, *, vf=None, vt=None, observed=date(2026, 4, 16),
           doc_id="d1", quote="q") -> Claim:
    return Claim(subject=subject, predicate=predicate, object=obj,
                 valid_from=vf, valid_to=vt, observed_at=observed, doc_id=doc_id, quote=quote)


# ---------------------------------------------------------------------------
# Basic ownership change
# ---------------------------------------------------------------------------

def test_owner_change_produces_closing():
    idx = ReconcileIndex()
    old = _claim("Alice Chen", "owns", "payments service")
    idx.extend([old])

    new = _claim("Dana Lee", "owns", "payments service",
                 vf=date(2026, 5, 12), observed=date(2026, 5, 12), doc_id="d2")
    closings = idx.reconcile([new])

    assert len(closings) == 1
    c = closings[0]
    assert c.subject == "Alice Chen"
    assert c.predicate == "owns"
    assert c.object == "payments service"
    assert c.valid_to == date(2026, 5, 12)
    assert c.doc_id == "d2"


def test_same_owner_no_closing():
    idx = ReconcileIndex()
    old = _claim("Alice Chen", "owns", "payments service")
    idx.extend([old])
    closings = idx.reconcile([_claim("Alice Chen", "owns", "payments service",
                                     vf=date(2026, 5, 1), observed=date(2026, 5, 1))])
    assert closings == []


# ---------------------------------------------------------------------------
# Scalar predicate (deadline moving twice = chain_freshness)
# ---------------------------------------------------------------------------

def test_deadline_moves_twice():
    idx = ReconcileIndex()
    d1 = _claim("migration", "deadline", "due", vf=date(2026, 4, 25), observed=date(2026, 4, 16))
    idx.extend([d1])

    d2 = _claim("migration", "deadline", "due", vf=date(2026, 5, 2),
                observed=date(2026, 4, 23), doc_id="d2")
    c1 = idx.reconcile([d2])
    assert len(c1) == 1 and c1[0].valid_to == date(2026, 5, 2)

    d3 = _claim("migration", "deadline", "due", vf=date(2026, 5, 9),
                observed=date(2026, 4, 30), doc_id="d3")
    c2 = idx.reconcile([d3])
    assert len(c2) == 1 and c2[0].valid_to == date(2026, 5, 9)


# ---------------------------------------------------------------------------
# Multi-valued predicates never auto-close
# ---------------------------------------------------------------------------

def test_works_on_not_closed():
    idx = ReconcileIndex()
    idx.extend([_claim("Alice Chen", "works_on", "atlas")])
    closings = idx.reconcile([_claim("Dana Lee", "works_on", "atlas", doc_id="d2")])
    assert closings == []


def test_member_of_not_closed():
    idx = ReconcileIndex()
    idx.extend([_claim("Alice Chen", "member_of", "platform team")])
    closings = idx.reconcile([_claim("Dana Lee", "member_of", "platform team", doc_id="d2")])
    assert closings == []


# ---------------------------------------------------------------------------
# LLM-emitted closing is not duplicated
# ---------------------------------------------------------------------------

def test_llm_closing_not_duplicated():
    idx = ReconcileIndex()
    idx.extend([_claim("Alice Chen", "owns", "payments service")])

    llm_closing = _claim("Alice Chen", "owns", "payments service",
                         vt=date(2026, 5, 12), observed=date(2026, 5, 12), doc_id="d2")
    new_open = _claim("Dana Lee", "owns", "payments service",
                      vf=date(2026, 5, 12), observed=date(2026, 5, 12), doc_id="d2")
    closings = idx.reconcile([new_open, llm_closing])
    assert closings == []  # already closed by LLM


# ---------------------------------------------------------------------------
# Cross-part: part_b closes part_a fact
# ---------------------------------------------------------------------------

def test_part_a_fact_closed_by_part_b(tmp_path):
    """Seed from part_a claims, then reconcile part_b — the closing appears."""
    part_a_claim = _claim("Alice Chen", "owns", "payments service",
                          observed=date(2026, 4, 16), doc_id="E:part_a_1")
    idx = ReconcileIndex()
    idx.extend([part_a_claim])

    part_b_claim = _claim("Dana Lee", "owns", "payments service",
                          vf=date(2026, 5, 12), observed=date(2026, 5, 12), doc_id="E:part_b_1")
    closings = idx.reconcile([part_b_claim])

    assert len(closings) == 1
    assert closings[0].subject == "Alice Chen"
    assert closings[0].doc_id == "E:part_b_1"


# ---------------------------------------------------------------------------
# attr: predicates behave as scalar
# ---------------------------------------------------------------------------

def test_attr_predicate_scalar():
    idx = ReconcileIndex()
    idx.extend([_claim("atlas", "attr:p95_latency", "120ms")])
    closings = idx.reconcile([_claim("atlas", "attr:p95_latency", "95ms",
                                     vf=date(2026, 5, 1), doc_id="d2")])
    assert len(closings) == 1 and closings[0].object == "120ms"


# ---------------------------------------------------------------------------
# Assigned_to behaves like owns (one assignee per thing)
# ---------------------------------------------------------------------------

def test_assigned_to_change():
    idx = ReconcileIndex()
    idx.extend([_claim("Alice Chen", "assigned_to", "ticket 42")])
    closings = idx.reconcile([_claim("Dana Lee", "assigned_to", "ticket 42",
                                     vf=date(2026, 5, 1), doc_id="d2")])
    assert len(closings) == 1 and closings[0].subject == "Alice Chen"


# ---------------------------------------------------------------------------
# Out-of-order documents never produce inverted intervals
# ---------------------------------------------------------------------------

def test_older_fact_processed_later_does_not_close_newer():
    # An August status is indexed first; a July doc arrives afterwards.
    idx = ReconcileIndex()
    august = _claim("camden row", "status", "current fire plan", vf=date(2027, 8, 22),
                    observed=date(2027, 8, 22), doc_id="aug")
    assert idx.reconcile([august]) == []

    july = _claim("camden row", "status", "carrying 6% contingency", vf=date(2027, 7, 23),
                  observed=date(2027, 7, 23), doc_id="jul")
    assert idx.reconcile([july]) == []

    # The August fact is still the open one: a September change closes it, not the July one.
    september = _claim("camden row", "status", "handed over", vf=date(2027, 9, 1),
                       observed=date(2027, 9, 1), doc_id="sep")
    [closing] = idx.reconcile([september])
    assert closing.object == "current fire plan"
    assert closing.valid_to == date(2027, 9, 1)


def test_reconcile_never_emits_valid_to_before_valid_from():
    idx = ReconcileIndex()
    days = [date(2027, 8, 22), date(2027, 7, 23), date(2027, 9, 2), date(2027, 8, 1), date(2027, 9, 10)]
    closings = []
    for i, d in enumerate(days):
        closings += idx.reconcile([_claim("camden row", "deadline", f"pour {i}", vf=d, observed=d, doc_id=f"d{i}")])
    assert closings
    assert all(c.valid_to >= c.valid_from for c in closings)
