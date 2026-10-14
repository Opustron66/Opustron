"""Application-facing memory API."""

from chronicle.schema import Event
from .database import MemoryDatabase


class MemoryAPI:
    def __init__(self, database: MemoryDatabase | None = None) -> None:
        self.database = database or MemoryDatabase()

    def remember(self, event: Event) -> Event:
        return self.database.add(event)

    def list_memories(self) -> list[Event]:
        return self.database.all()
