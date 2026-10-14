"""Memory retrieval for reasoning."""

from chronicle.memory.search import MemorySearch


def retrieve(question: str, search: MemorySearch):
    return search.search(question)
