from datetime import date

import pytest

from chronicle.memory.api import MemoryAPI
from chronicle.schema import Claim


def make_claim(subject, predicate, obj, *, observed, valid_from="observed", valid_to=None, doc=None, quote=None,
               confidence=1.0) -> Claim:
    """A claim shaped like P1's output: valid_from defaults to the document date."""
    observed = date.fromisoformat(observed)
    if valid_from == "observed":
        valid_from = None if valid_to else observed
    return Claim(
        subject=subject, predicate=predicate, object=obj,
        valid_from=valid_from, valid_to=valid_to, observed_at=observed,
        doc_id=doc or f"doc:{observed}", quote=quote or f"{subject} {predicate} {obj}.",
        confidence=confidence,
    )


def handover(new, old, thing, day, doc="E:handover"):
    """P1's two claims for 'Effective today, <new> takes over <thing> from <old>'."""
    quote = f"Effective today, {new} takes over the {thing} from {old}."
    return [
        make_claim(new, "owns", thing, observed=day, valid_from=day, doc=doc, quote=quote),
        make_claim(old, "owns", thing, observed=day, valid_from=None, valid_to=day, doc=doc, quote=quote),
    ]


@pytest.fixture
def claim():
    return make_claim


@pytest.fixture
def payments():
    """Alice owns payments from 16 Apr; Dana takes over on 12 May."""
    return [
        make_claim("Alice Chen", "owns", "payments service", observed="2026-04-16", doc="E:alice",
                   quote="Alice Chen owns the payments service."),
        *handover("Dana Lee", "Alice Chen", "payments service", "2026-05-12"),
    ]


@pytest.fixture
def memory():
    api = MemoryAPI()
    yield api
    api.close()
