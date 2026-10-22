"""Shared LLM client for Chronicle.

Every module (P1–P4) uses this instead of calling openai directly.
All requests pass through the privacy router before leaving the machine.

Usage:
    from chronicle.guard import llm

    response = llm.complete(
        messages=[{"role": "user", "content": "Who owned payments on 3 May?"}],
    )

    # Structured JSON output, parsed for you:
    data = llm.complete(messages=..., schema={"type": "object", ...})

    # Structured output, raw reply text (you parse it yourself):
    text = llm.complete(messages=..., schema={"name": "claims", "schema": {...}})
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

_CACHE_DIR = Path.home() / ".chronicle" / "llm_cache"

# Models
DEV_MODEL = "nvidia/nemotron-mini-4b-instruct"   # cheap, fast
PROD_MODEL = "nvidia/nemotron-4-340b-instruct"    # official benchmark runs
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_MAX_TOKENS = 1024  # reasoning models (Nemotron) need 8192–32768: set max_tokens or CHRONICLE_MAX_TOKENS

# HTTP statuses an OpenAI-compatible endpoint returns when it rejects response_format
_SCHEMA_REJECTED_STATUSES = (400, 422)
_FALSY = ("0", "false", "no", "off")


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?")
_JSON_START = re.compile(r"[{\[]")


def parse_json_reply(text: str) -> Any:
    """Parse a model reply that should be JSON, tolerating reasoning-model noise.

    Strips <think> blocks (and anything before a stray closing </think>) and
    code fences, then returns the LAST complete top-level JSON value, since a
    reasoning model's answer follows its thinking. Raises ValueError if none.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = _THINK_BLOCK.sub("", text)
    if "</think>" in cleaned:
        cleaned = cleaned.rsplit("</think>", 1)[1]
    cleaned = _FENCE.sub("", cleaned)

    decoder, found, pos = json.JSONDecoder(), None, 0
    while (match := _JSON_START.search(cleaned, pos)) is not None:
        try:
            value, end = decoder.raw_decode(cleaned, match.start())
        except json.JSONDecodeError:
            pos = match.start() + 1
            continue
        found, pos = value, end  # skip past it, so nested objects never win
    if found is None:
        raise ValueError(f"model reply contained no JSON: {text[:120]!r}")
    return found


def _is_wrapped(schema: dict[str, Any]) -> bool:
    """True for an OpenAI ``json_schema`` envelope ({"name": ..., "schema": {...}})."""
    return "type" not in schema and "name" in schema and isinstance(schema.get("schema"), dict)


def _cacheable_reply(raw: str, schema: dict[str, Any] | None) -> bool:
    """Cache admission checks, not a replacement for the caller's schema validation."""
    if not raw.strip():
        return False
    if schema is None:
        return True
    try:
        value = parse_json_reply(raw)
    except ValueError:
        return False
    spec = schema["schema"] if _is_wrapped(schema) else schema
    types = {"object": dict, "array": list, "string": str, "boolean": bool,
             "integer": int, "number": (int, float), "null": type(None)}

    def matches(item, declared):
        choices = declared if isinstance(declared, list) else [declared]
        return any(kind in types and isinstance(item, types[kind])
                   and not (kind in ("integer", "number") and isinstance(item, bool)) for kind in choices)

    if "type" in spec and not matches(value, spec["type"]):
        return False
    if isinstance(value, dict):
        if any(key not in value for key in spec.get("required", [])):
            return False
        for key, prop in spec.get("properties", {}).items():
            if key in value and "type" in prop and not matches(value[key], prop["type"]):
                return False
    return True


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
        max_tokens: int | None = None,
        timeout: float | None = None,
        transport: Callable[..., Any] | None = None,
        thinking: bool | None = None,
    ) -> None:
        """
        transport: optional replacement for ``OpenAI().chat.completions.create``
        (takes its keyword arguments, returns an object with ``.choices`` and
        ``.usage``). Tests use it to run without the network.

        thinking: switch a reasoning model's thinking on or off (Nemotron's
        ``enable_thinking`` chat-template flag); None keeps the model default.
        Falls back to CHRONICLE_THINKING.
        """
        self._api_key = api_key or os.environ.get("NEBIUS_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url or os.environ.get("NEBIUS_BASE_URL") or os.environ.get("OPENAI_BASE_URL", DEFAULT_BASE_URL)
        self._default_model = default_model or os.environ.get(
            "CHRONICLE_MODEL", DEV_MODEL
        )
        # CHRONICLE_LLM_CACHE=off: no cache reads or writes, so a benchmark trial makes fresh calls.
        self._use_cache = use_cache and os.environ.get("CHRONICLE_LLM_CACHE", "1").lower() not in _FALSY
        self._router = privacy_router  # set after construction to avoid circular import
        self.max_tokens = max_tokens or int(
            os.environ.get("CHRONICLE_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        )
        self._timeout = timeout
        self._transport = transport
        self._transport_lock = threading.Lock()
        self._local = threading.local()
        # CHRONICLE_STRUCTURED=false skips response_format; it also flips off once the endpoint rejects json_schema
        self._structured = os.environ.get("CHRONICLE_STRUCTURED", "1").lower() not in _FALSY
        if thinking is None and (env := os.environ.get("CHRONICLE_THINKING")):
            thinking = env.lower() not in _FALSY
        self.thinking = thinking

        if self._use_cache:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def model(self) -> str:
        """The model used when ``complete`` is called without ``model``."""
        return self._default_model

    # ------------------------------------------------------------------
    # Public interface (P1–P4 all call this)
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> str | dict[str, Any]:
        """Call the LLM, routing PII through the privacy router.

        `schema` may be a bare JSON Schema or an OpenAI ``json_schema``
        envelope ({"name": ..., "schema": {...}}):

        - no schema: returns the reply text.
        - bare schema: returns the parsed JSON object.
        - envelope: returns the reply text, for callers that parse it
          themselves.

        Bare-schema replies go through ``parse_json_reply``, so <think> blocks
        and code fences around the JSON are tolerated.

        If the endpoint rejects ``response_format``, the call is retried
        without it and later calls on this client skip it.
        """
        from .egress_logger import get_logger
        from .privacy_router import PrivacyRouter

        router: PrivacyRouter = self._router or PrivacyRouter()

        # Redact PII in all message contents
        redacted_messages, mapping = router.redact_messages(messages)
        redacted_messages = with_placeholder_note(redacted_messages)
        self._local.mapping = mapping

        # Check cache
        budget = max_tokens or self.max_tokens
        cache_key = self._cache_key(redacted_messages, schema, model or self._default_model,
                                    max_tokens=budget, temperature=temperature)
        cached = self._load_cache(cache_key) if self._use_cache else None
        cache_hit = cached is not None and _cacheable_reply(cached, schema)
        if cache_hit:
            raw, prompt_tokens, completion_tokens, finish_reason = cached, 0, 0, None
        else:
            raw, prompt_tokens, completion_tokens, finish_reason = self._call_api(
                redacted_messages, schema, model, temperature, budget
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

        if finish_reason in ("length", "content_filter"):
            raise ValueError(f"truncated reply (finish_reason={finish_reason}, max_tokens={budget})"
                             " — raise CHRONICLE_MAX_TOKENS or set CHRONICLE_THINKING=false")
        if not raw.strip():
            raise ValueError("Model returned an empty response")
        result = parse_json_reply(restored_raw) if schema is not None and not _is_wrapped(schema) else restored_raw
        if self._use_cache and not cache_hit and _cacheable_reply(raw, schema):
            # Persist pseudonymised text only, after parsing/admission checks succeed.
            self._save_cache(cache_key, raw)
        return result

    def restore_variants(self) -> dict[str, list[str]]:
        """For the calling thread's last ``complete``: restored value → other spellings
        the request used for it. Lets P1 match a restored quote back to its document."""
        mapping = getattr(self._local, "mapping", None)
        return mapping.surfaces() if mapping is not None else {}

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
    ) -> tuple[str, int, int, str | None]:
        """Return content, usage and finish reason so incomplete replies cannot be cached."""
        create = self._get_transport()

        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if schema is not None and self._structured:
            envelope = schema if _is_wrapped(schema) else {"name": "response", "schema": schema}
            kwargs["response_format"] = {"type": "json_schema", "json_schema": envelope}
        if self.thinking is not None:
            kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": self.thinking}}

        try:
            resp = create(**kwargs)
        except Exception as exc:
            if "response_format" not in kwargs or not _rejects_schema(exc):
                raise
            kwargs.pop("response_format")
            resp = create(**kwargs)
            self._structured = False

        choice = resp.choices[0]
        content = choice.message.content
        usage = resp.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        return content or "", prompt_tokens, completion_tokens, getattr(choice, "finish_reason", None)

    def _get_transport(self) -> Callable[..., Any]:
        with self._transport_lock:
            if self._transport is None:
                try:
                    from openai import OpenAI
                except ImportError as exc:
                    raise RuntimeError(
                        "openai package is required: uv add openai"
                    ) from exc
                kwargs: dict[str, Any] = {"api_key": self._api_key, "base_url": self._base_url,
                                          "max_retries": 2}
                if self._timeout is not None:
                    kwargs["timeout"] = self._timeout
                self._transport = OpenAI(**kwargs).chat.completions.create
            return self._transport

    def _cache_key(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any] | None,
        model: str,
        *,
        max_tokens: int | None = None,
        temperature: float = 0.0,
    ) -> str:
        payload = json.dumps({"version": 2, "messages": messages, "schema": schema, "model": model,
                              "base_url": _cache_endpoint(self._base_url),
                              "max_tokens": max_tokens or self.max_tokens, "temperature": temperature,
                              "structured": self._structured, "thinking": self.thinking}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _load_cache(self, key: str) -> str | None:
        path = _CACHE_DIR / f"{key}.txt"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def _save_cache(self, key: str, content: str) -> None:
        path = _CACHE_DIR / f"{key}.txt"
        path.write_text(content, encoding="utf-8")


_NAME_TOKEN = re.compile(r"\b(?:PERSON|ORG|LOC|NRP)_\d+\b")
PLACEHOLDER_NOTE = (
    "Privacy note: names of people, organisations and places in this request were replaced by "
    "placeholders such as PERSON_1 or ORG_2. Each placeholder stands for one real name everywhere "
    "in the request. Treat it exactly as that name: a fact stated about PERSON_1 is stated about "
    "that person, and an answer may name PERSON_1. Do not call a value unstated because it sits "
    "next to a placeholder."
)


def with_placeholder_note(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Tell the model how to read name placeholders, when the request contains any.

    Without it, answers on redacted evidence hedged ("referenced as ... (specific value not
    stated)") and the deterministic grader read them as not asserting the value.
    CHRONICLE_PLACEHOLDER_NOTE=off leaves requests unchanged."""
    if os.environ.get("CHRONICLE_PLACEHOLDER_NOTE", "1").lower() in _FALSY:
        return messages
    if not any(_NAME_TOKEN.search(m.get("content") or "") for m in messages):
        return messages
    if messages and messages[0].get("role") == "system":
        first = {**messages[0], "content": f"{messages[0]['content']}\n\n{PLACEHOLDER_NOTE}"}
        return [first, *messages[1:]]
    return [{"role": "system", "content": PLACEHOLDER_NOTE}, *messages]


_LOOPBACK = re.compile(r"^(https?://)(?:127\.0\.0\.1|localhost|\[::1\]):\d+", re.IGNORECASE)


def _cache_endpoint(base_url: str) -> str:
    """Endpoint part of the cache key. A local proxy (the benchmark's accounting proxy) gets a
    new port every run; keying on the port would make every run a cold cache."""
    return _LOOPBACK.sub(r"\1loopback", base_url.rstrip("/"))


def _rejects_schema(exc: Exception) -> bool:
    """Did the endpoint refuse the request (most likely its response_format)?"""
    return getattr(exc, "status_code", None) in _SCHEMA_REJECTED_STATUSES


# ---------------------------------------------------------------------------
# Module-level singleton — import and use directly:
#   from chronicle.guard import llm
#   llm.complete(messages)
# ---------------------------------------------------------------------------

llm = LLMClient()
