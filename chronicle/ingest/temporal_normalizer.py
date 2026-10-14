"""Temporal normalization utilities."""

from datetime import datetime


def normalize(value: str | datetime | None) -> datetime | None:
    """Normalize an ISO-8601 value, leaving missing values as ``None``."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
