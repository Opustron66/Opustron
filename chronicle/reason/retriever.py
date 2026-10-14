from datetime import date
from typing import Protocol
from .models import Evidence, QueryPlan

class MemoryReader(Protocol):
    def find_facts(self, entity: str, predicate: str) -> list[Evidence]: ...

class MockMemoryReader:
    """Replace with P2's memory API adapter once available."""
    def __init__(self) -> None:
        self.facts = [
            Evidence("payments", "manager", "Alice", date(2026, 4, 1), date(2026, 5, 1), "email_001", "Alice manages payments."),
            Evidence("payments", "manager", "Bob", date(2026, 5, 1), None, "email_002", "Bob takes over payments on May 1."),
        ]

    def find_facts(self, entity: str, predicate: str) -> list[Evidence]:
        return [f for f in self.facts if f.subject == entity and f.predicate == predicate]

def retrieve(plan: QueryPlan, memory: MemoryReader, today: date) -> list[Evidence]:
    if plan.question_type == "unsupported" or not plan.entity or not plan.predicate:
        return []
    target = plan.reference_date if plan.reference_date is not None else today
    return [f for f in memory.find_facts(plan.entity, plan.predicate)
            if f.valid_from <= target and (f.valid_to is None or target < f.valid_to)]
