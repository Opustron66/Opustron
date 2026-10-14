"""LLM client boundary."""


class LLMClient:
    def complete(self, prompt: str) -> str:
        raise NotImplementedError("Configure an LLM provider before making requests")
