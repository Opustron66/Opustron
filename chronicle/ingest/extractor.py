"""Entity and fact extraction hooks."""

from chronicle.schema import Entity, Event


def extract_entities(event: Event) -> list[Entity]:
    """Return a conservative set of capitalized names from event content."""
    words = event.content.replace(",", " ").split()
    names = []
    for word in words:
        candidate = word.strip(".!?():;\"'")
        if candidate and candidate[0].isupper() and candidate not in {"The", "A", "I", "Met"}:
            names.append(Entity(name=candidate))
    return names
