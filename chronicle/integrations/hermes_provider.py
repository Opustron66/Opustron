"""Hermes provider integration boundary."""


class HermesProvider:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
