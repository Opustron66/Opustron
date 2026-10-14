"""Routing policy for local and external processing."""


def route(text: str, *, contains_pii: bool) -> str:
    return "local" if contains_pii else "external"
