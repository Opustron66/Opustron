"""Answer composition."""


def answer(question: str, memories: list) -> str:
    if not memories:
        return "I don't have enough information to answer that."
    return "\n".join(memory.content for memory in memories)
