"""Tavily search integration boundary."""


class TavilyClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
