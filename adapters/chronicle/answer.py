"""Benchmark adapter answer entry point."""

from chronicle.reason.pipeline import ReasoningPipeline


def answer(question: str, search):
    return ReasoningPipeline(search).ask(question)
