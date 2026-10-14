"""Composable ingestion pipeline."""

from collections.abc import Iterable

from .entity_resolver import resolve
from .extractor import extract_entities
from chronicle.schema import Event


class IngestPipeline:
    def process(self, events: Iterable[Event]) -> list[Event]:
        """Extract and resolve entities for each incoming event."""
        processed = []
        for event in events:
            event.entities = resolve(extract_entities(event))
            processed.append(event)
        return processed
