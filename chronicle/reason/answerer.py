from .models import Evidence

def format_answer(evidence: list[Evidence]) -> dict[str, object]:
    """Internal answer shape, NOT NVIDIA's final ANSWER_CONTRACT."""
    return {"answer": evidence[0].object, "citations": sorted({f.doc_id for f in evidence})}

def abstain() -> dict[str, object]:
    return {"answer": "Not enough information", "citations": []}
