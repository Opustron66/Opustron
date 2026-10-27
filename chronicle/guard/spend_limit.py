"""Hard spending cap for model calls, enforced before anything is sent.

Token Factory has budget alerts but no hard cap, and charges the card once the
balance hits $0. Set ``CHRONICLE_SPEND_LIMIT_USD`` (and ``CHRONICLE_SPEND_SINCE``,
an ISO timestamp, to count only spend after e.g. a top-up) and every call is
refused once the egress log shows that much spent. The egress log is shared by
every process, so the cap holds across a benchmark's ingest and answer phases.
"""

from __future__ import annotations

import os
from typing import Any

# USD per 1M tokens (input, output), from Token Factory's endpoints page (Oct 2026).
PRICES: dict[str, tuple[float, float]] = {
    "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
    "nvidia/Nemotron-3_5-Lightning": (0.06, 0.24),
}
_UNKNOWN_MODEL_PRICE = (1.00, 3.00)  # priced like Ultra, so the cap errs on the safe side


class SpendLimitReached(ValueError):
    """Raised instead of making a call. A ValueError so callers treat it as final, not retryable."""


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, _UNKNOWN_MODEL_PRICE)
    return prompt_tokens / 1e6 * price_in + completion_tokens / 1e6 * price_out


def spent_usd(records: list[dict[str, Any]], since: str = "") -> float:
    """Model spend in egress records at or after ``since``. Cache hits cost nothing."""
    return sum(
        cost_usd(r.get("model", ""), r.get("prompt_tokens", 0), r.get("completion_tokens", 0))
        for r in records
        if r.get("provider") == "nebius_token_factory" and not r.get("cached") and r.get("ts", "") >= since
    )


def check(records_loader) -> None:
    """Raise SpendLimitReached if the configured limit has been reached. No limit set: no-op."""
    limit = os.environ.get("CHRONICLE_SPEND_LIMIT_USD", "").strip()
    if not limit:
        return
    spent = spent_usd(records_loader(), os.environ.get("CHRONICLE_SPEND_SINCE", "").strip())
    if spent >= float(limit):
        raise SpendLimitReached(
            f"spending cap reached: ${spent:.2f} of ${float(limit):.2f} (CHRONICLE_SPEND_LIMIT_USD); call not sent"
        )
