"""NVIDIA benchmark input parser."""

from chronicle.schema import Event, Source


def parse(record: dict, *, uri: str = "memory://benchmark") -> Event:
    """Parse a benchmark record while retaining its original fields."""
    return Event(
        content=str(record.get("text", record.get("question", ""))),
        source=Source(uri=uri, kind="benchmark"),
        metadata=dict(record),
    )
