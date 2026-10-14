"""In-memory database implementation for the initial scaffold."""

from chronicle.schema import Event


class MemoryDatabase:
    def __init__(self) -> None:
        self._events: dict[str, Event] = {}

    def add(self, event: Event) -> Event:
        self._events[event.event_id] = event
        return event

    def all(self) -> list[Event]:
        return list(self._events.values())
