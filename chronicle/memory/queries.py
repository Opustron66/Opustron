"""Memory query helpers."""

from chronicle.schema import Event


def containing(events: list[Event], phrase: str) -> list[Event]:
    needle = phrase.casefold()
    return [event for event in events if needle in event.content.casefold()]
