"""Search interface for temporal memories."""

from .queries import containing
from .database import MemoryDatabase


class MemorySearch:
    def __init__(self, database: MemoryDatabase) -> None:
        self.database = database

    def search(self, phrase: str):
        return containing(self.database.all(), phrase)
