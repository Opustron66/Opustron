from .models import Evidence

def has_unambiguous_support(evidence: list[Evidence]) -> bool:
    """Conservative: abstain on no evidence or conflicting values."""
    return bool(evidence) and len({f.object for f in evidence}) == 1
