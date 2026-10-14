"""Basic PII detection hooks."""

import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")


def contains_email(text: str) -> bool:
    return EMAIL.search(text) is not None
