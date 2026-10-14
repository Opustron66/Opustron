"""Chat message parser."""

from typing import Any

from chronicle.schema import Event, Source


def parse(message: dict[str, Any], *, uri: str = "memory://chat") -> Event:
    """Parse a chat message into an event."""
    return Event(
        content=str(message.get("content", "")),
        source=Source(uri=uri, kind="chat"),
        metadata=dict(message),
    )
