"""Shared domain models used across Chronicle."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class Source:
    uri: str
    kind: str
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Entity:
    name: str
    entity_type: str = "unknown"
    entity_id: str = field(default_factory=lambda: str(uuid4()))
    aliases: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Event:
    content: str
    source: Source
    occurred_at: datetime | None = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    entities: list[Entity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
