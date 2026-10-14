"""PII pseudonymization."""

from .pii_detector import EMAIL


def pseudonymize(text: str) -> str:
    return EMAIL.sub("[EMAIL]", text)
