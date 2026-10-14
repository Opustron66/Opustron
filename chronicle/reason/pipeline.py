"""End-to-end reasoning pipeline."""

from chronicle.memory.search import MemorySearch
from .answerer import answer
from .retriever import retrieve


class ReasoningPipeline:
    def __init__(self, search: MemorySearch) -> None:
        self.search = search

    def ask(self, question: str) -> str:
        return answer(question, retrieve(question, self.search))
