"""Supersession: when a newer fact closes an older one.

Some predicates hold one value at a time. Those facts compete in a *slot*: a payments service has
one owner, a person has one manager. When a different value starts, the previous value stops, so
"Dana owns payments from 12 May" closes "Alice owns payments" at 12 May. Nothing is deleted; the
old fact just gets a ``valid_to`` and a ``superseded_by``.

Which side of the triple is the slot depends on the predicate:

* ``owns``: one owner per *object* (``Dana owns payments`` competes with ``Alice owns payments``).
* ``status``, ``reports_to``, ``role`` ...: one value per *subject*.
* ``works_on``, ``member_of``, ``related_to`` ...: many at once, never auto-superseded. They end
  only when a source says so.

Slot timelines are recomputed from every fact in the slot (``resolve_slot``), so the result does
not depend on the order documents were ingested in.
"""

import re
from dataclasses import dataclass

# One owner/lead per thing: slot = (predicate, object), the subject competes.
SINGLE_PER_OBJECT = frozenset({"owns", "leads", "manages", "maintains"})
# One value per subject: slot = (subject, predicate), the object competes.
SINGLE_PER_SUBJECT = frozenset({
    "status", "deadline", "scheduled_for", "located_in", "reports_to", "works_at", "role",
    "owner", "owned_by", "lead", "led_by", "assigned_to", "on_call", "manager", "managed_by", "title",
})
# The object is a placeholder ("due") and the date is the real value: P1 puts the date in
# valid_from. These facts become true when they are *stated* (observed_at), and a later statement
# with a different date replaces the earlier one.
DATED = frozenset({"deadline", "scheduled_for"})


def normalize_predicate(predicate: str) -> str:
    return re.sub(r"[\s\-]+", "_", predicate.strip().casefold())


def normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def slot_for(subject_key: str, predicate: str, object_key: str) -> tuple[str | None, str | None]:
    """Return ``(slot, value)`` for a fact, or ``(None, None)`` if it never auto-supersedes."""
    if predicate in SINGLE_PER_OBJECT:
        return f"{predicate}|obj|{object_key}", subject_key
    if predicate in SINGLE_PER_SUBJECT:
        return f"{predicate}|subj|{subject_key}", object_key
    return None, None


@dataclass(frozen=True, slots=True)
class SlotMember:
    fact_id: str
    value: str
    start: str | None       # stated start (store timestamp); None = unknown
    stated_end: str | None  # earliest end any source stated
    stated_reason: str | None
    observed: str | None    # when the opening statement was made
    seq: int                # insertion order, last-resort tie break


@dataclass(frozen=True, slots=True)
class Resolution:
    valid_to: str | None
    superseded_by: str | None
    end_reason: str | None


def resolve_slot(members: list[SlotMember]) -> dict[str, Resolution]:
    """Work out where each fact in a slot ends.

    A fact ends at the earlier of its stated end and the start of the first *different* value
    that starts after it. Two values starting at the same moment: the one stated later wins and
    the other gets an empty interval (kept for history, never true in as-of queries). A fact with
    an unknown start (only its closing was ever stated) is never superseded; it ends where its
    source says.
    """
    result = {}
    for fact in members:
        challenger = None
        if fact.start is not None:
            rivals = [
                other for other in members
                if other.value != fact.value and other.start is not None
                and (other.start, other.observed or "", other.seq) > (fact.start, fact.observed or "", fact.seq)
            ]
            challenger = min(rivals, key=lambda o: (o.start, o.observed or "", o.seq), default=None)
        if challenger and (fact.stated_end is None or challenger.start <= fact.stated_end):
            result[fact.fact_id] = Resolution(challenger.start, challenger.fact_id, "superseded")
        elif fact.stated_end is not None:
            result[fact.fact_id] = Resolution(fact.stated_end, None, fact.stated_reason or "stated")
        else:
            result[fact.fact_id] = Resolution(None, None, None)
    return result
