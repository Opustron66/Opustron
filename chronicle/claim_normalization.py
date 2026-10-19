"""Small shared normalizations for P1 output and P2 claim ingestion."""
import re

DATED_PREDICATES = frozenset({"deadline", "scheduled_for"})
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def normalize_claim_value(predicate: str, value: str) -> tuple[str, str]:
    predicate = re.sub(r"[\s-]+", "_", predicate.strip().casefold())
    value = value.strip()
    if predicate in {"status", "email", "work_email", "contact_email", "email_address"} and _EMAIL.fullmatch(value):
        return "email", value
    if predicate == "deadline" and value.casefold() in {"due", "deadline", "due date"}:
        value = "due"
    elif predicate == "scheduled_for" and value.casefold() in {"scheduled", "schedule", "scheduled for"}:
        value = "scheduled"
    return predicate, value
