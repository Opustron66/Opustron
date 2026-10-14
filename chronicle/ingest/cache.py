"""Small in-memory ingestion cache."""

from chronicle.schema import Event


class IngestCache:
    def __init__(self) -> None:
        self._events: dict[str, Event] = {}

    def get(self, key: str) -> Event | None:
        return self._events.get(key)

    def put(self, key: str, event: Event) -> None:
        self._events[key] = event
