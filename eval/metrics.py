"""Evaluation metrics."""


def exact_match(prediction: str, expected: str) -> float:
    return float(prediction.strip().casefold() == expected.strip().casefold())
