"""Shared LLM client for Chronicle.

Every module (P1–P4) uses this instead of calling openai directly.
All requests pass through the privacy router before leaving the machine.

Usage:
    from chronicle.guard import llm

    response = llm.complete(
        messages=[{"role": "user", "content": "Who owned payments on 3 May?"}],
    )

    # Structured JSON output:
    data = llm.complete(messages=..., schema={"type": "object", ...})
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

_CACHE_DIR = Path.home() / ".chronicle" / "llm_cache"

# Models
DEV_MODEL = "nvidia/nemotron-mini-4b-instruct"   # cheap, fast
PROD_MODEL = "nvidia/nemotron-4-340b-instruct"    # official benchmark runs
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


class LLMClient:
    """OpenAI-compatible client wired to Nebius Token Factory."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        use_cache: bool = True,
        privacy_router: Any | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("NEBIUS_API_KEY", "")
        self._base_url = base_url or os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL)
        self._default_model = default_model or os.environ.get(
            "CHRONICLE_MODEL", DEV_MODEL
        )
        self._use_cache = use_cache
        self._router = privacy_router  # set after construction to avoid circular import

        if use_cache:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public interface (P1–P4 all call this)
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str | dict[str, Any]:
        """Call the LLM, routing PII through the privacy router.

        Returns a string unless `schema` is provided, in which case it
        returns the parsed JSON object.
        """
        from .egress_logger import get_logger
        from .privacy_router import PrivacyRouter

        router: PrivacyRouter = self._router or PrivacyRouter()

        # Redact PII in all message contents
        redacted_messages, mapping = router.redact_messages(messages)

        # Check cache
        cache_key = self._cache_key(redacted_messages, schema, model or self._default_model)
        if self._use_cache:
            cached = self._load_cache(cache_key)
            if cached is not None:
                raw = cached
                prompt_tokens = completion_tokens = 0
            else:
                raw, prompt_tokens, completion_tokens = self._call_api(
                    redacted_messages, schema, model, temperature, max_tokens
                )
                self._save_cache(cache_key, raw)
        else:
            raw, prompt_tokens, completion_tokens = self._call_api(
                redacted_messages, schema, model, temperature, max_tokens
            )

        # Re-identify pseudonyms in the response
        restored_raw = router.restore(raw, mapping)

        # Log egress
        get_logger().log(
            provider="nebius_token_factory",
            model=model or self._default_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            redacted=mapping is not None and bool(mapping.pii_types_seen()),
            pii_types=mapping.pii_types_seen() if mapping else [],
            request_preview=redacted_messages[-1]["content"][:200] if redacted_messages else "",
        )

        if schema is not None:
            try:
                return json.loads(restored_raw)
            except json.JSONDecodeError:
                # Best-effort: strip markdown fences and retry
                stripped = restored_raw.strip().removeprefix("```json").removesuffix("```").strip()
                return json.loads(stripped)

        return restored_raw

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _call_api(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        model: str | None,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        """Make the actual API call. Returns (content, prompt_tokens, completion_tokens)."""
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "openai package is required: uv add openai"
            ) from exc

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)

        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema},
            }

        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content or ""
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        return content, prompt_tokens, completion_tokens

    def _cache_key(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        model: str,
    ) -> str:
        payload = json.dumps({"messages": messages, "schema": schema, "model": model}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _load_cache(self, key: str) -> str | None:
        path = _CACHE_DIR / f"{key}.txt"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def _save_cache(self, key: str, content: str) -> None:
        path = _CACHE_DIR / f"{key}.txt"
        path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly:
#   from chronicle.guard import llm
#   llm.complete(messages)
# ---------------------------------------------------------------------------

llm = LLMClient()
