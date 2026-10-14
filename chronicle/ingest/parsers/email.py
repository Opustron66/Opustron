"""Email parser."""

from typing import Any

from chronicle.schema import Event, Source


def parse(message: dict[str, Any], *, uri: str = "memory://email") -> Event:
    """Parse a normalized email record."""
    subject = str(message.get("subject", "")).strip()
    body = str(message.get("body", "")).strip()
    content = f"{subject}\n\n{body}".strip()
    return Event(content=content, source=Source(uri=uri, kind="email"), metadata=dict(message))
