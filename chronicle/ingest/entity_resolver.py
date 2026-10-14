"""Entity resolution helpers."""

from chronicle.schema import Entity


def resolve(entities: list[Entity]) -> list[Entity]:
    """Deduplicate entities by case-insensitive name."""
    unique: dict[str, Entity] = {}
    for entity in entities:
        unique.setdefault(entity.name.casefold(), entity)
    return list(unique.values())
