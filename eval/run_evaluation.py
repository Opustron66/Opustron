"""Run Chronicle evaluations."""

from .metrics import exact_match


def run(cases: list[dict[str, str]]) -> float:
    if not cases:
        return 0.0
    return sum(exact_match(case["prediction"], case["expected"]) for case in cases) / len(cases)
