"""Abstention policy."""


def should_abstain(memories: list, *, minimum: int = 1) -> bool:
    return len(memories) < minimum
