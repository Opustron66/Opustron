"""Default OpenAI-compatible LLM client for ingestion (Nebius Token Factory).

Interim implementation: P4's ``chronicle.guard.llm_client`` is the long-term, privacy-routed
replacement; both satisfy the ``LLM`` protocol in ``extractor.py``.
"""

import os
import threading
from typing import Any

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


class OpenAICompatLLM:
    def __init__(self, model: str | None = None, base_url: str | None = None, api_key: str | None = None,
                 timeout: float = 180, max_tokens: int = 4096, thinking: bool = False) -> None:
        from openai import OpenAI

        self.model = model or os.environ.get("CHRONICLE_MODEL") or os.environ.get("MNEMO_MODEL", "")
        if not self.model:
            raise RuntimeError("Set CHRONICLE_MODEL (or pass --model) to a Nemotron model id")
        self.client = OpenAI(
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL),
            api_key=api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("NEBIUS_API_KEY"),
            timeout=timeout,
            max_retries=2,
        )
        self.max_tokens = max_tokens
        self.thinking = thinking  # Nemotron's visible reasoning is ~10x slower and can exhaust max_tokens
        self.prompt_tokens = self.completion_tokens = self.calls = 0
        self._lock = threading.Lock()
        self.structured = True  # flips to False if the endpoint rejects json_schema

    def complete(self, messages: list[dict[str, str]], schema: dict[str, Any] | None = None) -> str:
        kwargs: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": 0, "max_tokens": self.max_tokens}
        if not self.thinking:
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
        if schema and self.structured:
            kwargs["response_format"] = {"type": "json_schema", "json_schema": schema}
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except Exception:
            if "response_format" not in kwargs:
                raise
            self.structured = False
            kwargs.pop("response_format")
            resp = self.client.chat.completions.create(**kwargs)
        if resp.usage:
            with self._lock:
                self.calls += 1
                self.prompt_tokens += resp.usage.prompt_tokens or 0
                self.completion_tokens += resp.usage.completion_tokens or 0
        choice = resp.choices[0]
        if choice.finish_reason == "length":  # truncated: never parse half an answer
            raise ValueError(f"LLM reply truncated at max_tokens={self.max_tokens}")
        return choice.message.content or ""
