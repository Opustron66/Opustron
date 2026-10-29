"""Durable, atomic Lightning budget over Upstash REST; never initialized on startup.

Reservations cover a full 1,048,576-token input context plus maximum output.
Confirmed usage refunds the difference. Ambiguous failures keep the reservation.
No TTLs: losing the ledger must stop calls, never replenish the budget.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import uuid
from decimal import ROUND_CEILING, Decimal
from urllib.parse import urlsplit

import httpx

from .spend_limit import SpendLimitReached

MODEL = "nvidia/Nemotron-3_5-Lightning"
CONTEXT_TOKENS = 1_048_576
MICRO = Decimal(1_000_000)

INIT = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], 'limit', ARGV[1], 'spent', 0, 'version', 1)
return 1
"""

RESERVE = """
local limit = tonumber(redis.call('HGET', KEYS[1], 'limit'))
local spent = tonumber(redis.call('HGET', KEYS[1], 'spent'))
if not limit or not spent or spent < 0 or spent % 1 ~= 0 or
   limit ~= tonumber(ARGV[1]) or redis.call('HGET', KEYS[1], 'version') ~= '1' or
   redis.call('PTTL', KEYS[1]) ~= -1 then return -2 end
local amount = tonumber(ARGV[2])
if spent + amount > limit then return -1 end
if redis.call('HEXISTS', KEYS[1], ARGV[3]) == 1 then return -2 end
redis.call('HINCRBY', KEYS[1], 'spent', amount)
redis.call('HSET', KEYS[1], ARGV[3], amount)
return amount
"""

SETTLE = """
local held = tonumber(redis.call('HGET', KEYS[1], ARGV[1]))
local spent = tonumber(redis.call('HGET', KEYS[1], 'spent'))
local actual = tonumber(ARGV[2])
if not held or not spent or spent < held or actual < 0 or actual > held or
   redis.call('PTTL', KEYS[1]) ~= -1 then return -2 end
redis.call('HINCRBY', KEYS[1], 'spent', actual - held)
redis.call('HDEL', KEYS[1], ARGV[1])
return 1
"""


class BudgetUnavailable(ValueError):
    """The shared ledger could not safely authorize a model call."""


def enabled() -> bool:
    backend = os.environ.get("CHRONICLE_SPEND_BACKEND", "local")
    if backend not in {"local", "upstash"}:
        raise BudgetUnavailable("Unknown CHRONICLE_SPEND_BACKEND")
    return backend == "upstash"


def micros(value: str) -> int:
    try:
        amount = Decimal(value)
        if not amount.is_finite() or not 0 < amount <= 1000 or amount * MICRO != (amount * MICRO).to_integral_value():
            raise ValueError
        return int(amount * MICRO)
    except (ValueError, ArithmeticError):
        raise BudgetUnavailable("Set CHRONICLE_SPEND_LIMIT_USD to a positive amount, at most $1000 and six decimal places") from None


def token_cost(prompt: int, completion: int) -> int:
    # USD per million tokens equals micro-USD per token. Always round up.
    return int((Decimal(prompt) * Decimal("0.06") + Decimal(completion) * Decimal("0.24")).to_integral_value(rounding=ROUND_CEILING))


class RemoteBudget:
    def __init__(self) -> None:
        self.url = os.environ.get("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
        parsed = urlsplit(self.url)
        if (parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".upstash.io")
                or parsed.netloc != parsed.hostname or parsed.path or parsed.query or parsed.fragment or not self.token):
            raise BudgetUnavailable("Configure the Upstash HTTPS REST URL and regular REST token")
        budget_id = os.environ.get("CHRONICLE_SPEND_BUDGET_ID", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", budget_id):
            raise BudgetUnavailable("Set a stable CHRONICLE_SPEND_BUDGET_ID (letters, digits, _ or -)")
        self.key = f"chronicle:budget:{budget_id}"
        self.limit = micros(os.environ.get("CHRONICLE_SPEND_LIMIT_USD", ""))
        if os.environ.get("CHRONICLE_MODEL", MODEL) != MODEL:
            raise BudgetUnavailable("The Upstash demo budget supports only nvidia/Nemotron-3_5-Lightning")

    def command(self, *args):
        try:
            # No automatic HTTP retries: ambiguous writes must not be replayed.
            with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
                response = client.post(self.url, headers={"Authorization": f"Bearer {self.token}"}, json=list(args))
            response.raise_for_status()
            body = response.json()
            if "error" in body or "result" not in body:
                raise ValueError
            return body["result"]
        except (httpx.HTTPError, ValueError, TypeError, KeyError):
            # Neither credentials nor the service's raw error belong in public responses.
            raise BudgetUnavailable("Budget service unavailable; model request blocked") from None

    def initialize(self) -> None:
        if self.command("EVAL", INIT, 1, self.key, self.limit) != 1:
            raise BudgetUnavailable("Budget already exists; initialization will not reset it")

    def status(self) -> dict[str, int]:
        result = self.command("HMGET", self.key, "limit", "spent", "version")
        try:
            cap, spent, version = map(int, result)
            if cap != self.limit or spent < 0 or version != 1 or self.command("PTTL", self.key) != -1:
                raise ValueError
        except (ValueError, TypeError):
            raise BudgetUnavailable("Budget missing, expired or mismatched; initialize it once and keep its ID and limit unchanged") from None
        return {"limit_microusd": cap, "spent_or_reserved_microusd": spent}

    def reserve(self, model: str, max_tokens: int) -> str:
        if model != MODEL or type(max_tokens) is not int or not 0 < max_tokens <= CONTEXT_TOKENS:
            raise BudgetUnavailable("Unsupported model or output limit for the demo budget")
        receipt = f"request:{uuid.uuid4().hex}"
        amount = token_cost(CONTEXT_TOKENS, max_tokens)
        result = self.command("EVAL", RESERVE, 1, self.key, self.limit, amount, receipt)
        if result == -1:
            raise SpendLimitReached("Demo budget has insufficient funds for another model request")
        if result != amount:
            raise BudgetUnavailable("Budget missing, expired or mismatched; model request blocked")
        return receipt

    def settle(self, receipt: str, prompt: int, completion: int) -> None:
        if type(prompt) is not int or type(completion) is not int or min(prompt, completion) < 0 or prompt + completion == 0:
            raise BudgetUnavailable("Missing or invalid model usage; reservation retained")
        if self.command("EVAL", SETTLE, 1, self.key, receipt, token_cost(prompt, completion)) != 1:
            raise BudgetUnavailable("Model usage could not be settled; reservation retained")


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize once or inspect the durable demo budget; never calls a model")
    parser.add_argument("action", choices=["init", "status"])
    action = parser.parse_args().action
    budget = RemoteBudget()
    if action == "init":
        budget.initialize()
    print(json.dumps(budget.status()))


if __name__ == "__main__":
    main()
