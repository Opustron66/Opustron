"""Markdown parser."""

from chronicle.schema import Event, Source


def parse(text: str, *, uri: str = "memory://markdown") -> list[Event]:
    """Convert non-empty Markdown paragraphs into events."""
    return [
        Event(content=paragraph.strip(), source=Source(uri=uri, kind="markdown"))
        for paragraph in text.split("\n\n")
        if paragraph.strip()
    ]
