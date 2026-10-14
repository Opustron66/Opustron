"""Calendar event parser."""

from datetime import datetime
from typing import Any

from chronicle.schema import Event, Source


def parse(item: dict[str, Any], *, uri: str = "memory://calendar") -> Event:
    """Parse a calendar record with an ISO-8601 start time."""
    value = item.get("start")
    occurred_at = datetime.fromisoformat(value) if isinstance(value, str) else None
    return Event(
        content=str(item.get("summary", "")),
        source=Source(uri=uri, kind="calendar"),
        occurred_at=occurred_at,
        metadata=dict(item),
    )
