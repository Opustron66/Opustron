"""Supersession relationships between memories."""

from chronicle.schema import Event


def supersedes(current: Event, previous: Event) -> bool:
    """Return whether the current event explicitly supersedes a prior event."""
    return current.metadata.get("supersedes") == previous.event_id
