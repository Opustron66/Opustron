"""Durable, atomic Nemotron budget over Upstash REST; never initialized on startup.

Reservations cover a full 1,048,576-token input context plus maximum output.
Confirmed usage refunds the difference. Ambiguous failures keep the reservation.
No TTLs: losing the ledger must stop calls, never replenish the budget.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import uuid
from decimal import ROUND_CEILING, Decimal
from functools import lru_cache
from urllib.parse import urlsplit

import httpx

from .spend_limit import PRICES, SpendLimitReached

MODEL = "nvidia/Nemotron-3_5-Lightning"
ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"
SUPPORTED_MODELS = {MODEL, ULTRA}
CONTEXT_TOKENS = 1_048_576
MICRO = Decimal(1_000_000)


@lru_cache(maxsize=1)
def _http_client() -> httpx.Client:
    # The sync client is thread-safe. Reuse TLS connections between reservations
    # and settlements without retrying any ambiguous budget write.
    client = httpx.Client(timeout=5, follow_redirects=False, trust_env=False,
                          limits=httpx.Limits(max_connections=4, max_keepalive_connections=2))
    atexit.register(client.close)
    return client

INIT = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('HSET', KEYS[1], 'limit', ARGV[1], 'spent', 0, 'version', 1)
return 1
"""

RAISE_LIMIT = """
local limit = tonumber(redis.call('HGET', KEYS[1], 'limit'))
local spent = tonumber(redis.call('HGET', KEYS[1], 'spent'))
local target = tonumber(ARGV[2])
if not limit or not spent or spent < 0 or spent % 1 ~= 0 or
   limit ~= tonumber(ARGV[1]) or target <= limit or target < spent or
   redis.call('HGET', KEYS[1], 'version') ~= '1' or
   redis.call('PTTL', KEYS[1]) ~= -1 then return 0 end
redis.call('HSET', KEYS[1], 'limit', target)
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


def token_cost(prompt: int, completion: int, model: str = MODEL) -> int:
    # USD per million tokens equals micro-USD per token. Always round up.
    if model not in SUPPORTED_MODELS:
        raise BudgetUnavailable("Unsupported model for the demo budget")
    price_in, price_out = (Decimal(str(p)) for p in PRICES[model])
    return int((Decimal(prompt) * price_in + Decimal(completion) * price_out).to_integral_value(rounding=ROUND_CEILING))


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
        if os.environ.get("CHRONICLE_MODEL", MODEL) not in SUPPORTED_MODELS:
            raise BudgetUnavailable("The Upstash demo budget supports Nemotron 3.5 Lightning and Nemotron 3 Ultra")

    def command(self, *args):
        try:
            # No automatic HTTP retries: ambiguous writes must not be replayed.
            response = _http_client().post(self.url, headers={"Authorization": f"Bearer {self.token}"}, json=list(args))
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

    def raise_limit(self, target: str) -> None:
        new_limit = micros(target)
        if new_limit <= self.limit:
            raise BudgetUnavailable("The new limit must exceed the existing limit")
        if self.command("EVAL", RAISE_LIMIT, 1, self.key, self.limit, new_limit) != 1:
            raise BudgetUnavailable("Limit unchanged: ledger missing, expired, corrupt or old limit does not match")
        self.limit = new_limit

    def status(self) -> dict[str, int]:
        result = self.command("HMGET", self.key, "limit", "spent", "version")
        try:
            cap, spent, version = map(int, result)
            if cap != self.limit or spent < 0 or version != 1 or self.command("PTTL", self.key) != -1:
                raise ValueError
        except (ValueError, TypeError):
            raise BudgetUnavailable("Budget missing, expired or mismatched; use the existing ID and matching limit, or raise-limit for an intentional increase") from None
        return {"limit_microusd": cap, "spent_or_reserved_microusd": spent}

    def reserve(self, model: str, max_tokens: int) -> str:
        if model not in SUPPORTED_MODELS or type(max_tokens) is not int or not 0 < max_tokens <= CONTEXT_TOKENS:
            raise BudgetUnavailable("Unsupported model or output limit for the demo budget")
        receipt = f"request:{uuid.uuid4().hex}:{model}"
        amount = token_cost(CONTEXT_TOKENS, max_tokens, model)
        result = self.command("EVAL", RESERVE, 1, self.key, self.limit, amount, receipt)
        if result == -1:
            raise SpendLimitReached("Demo budget has insufficient funds for another model request")
        if result != amount:
            raise BudgetUnavailable("Budget missing, expired or mismatched; model request blocked")
        return receipt

    def settle(self, receipt: str, prompt: int, completion: int) -> None:
        if type(prompt) is not int or type(completion) is not int or min(prompt, completion) < 0 or prompt + completion == 0:
            raise BudgetUnavailable("Missing or invalid model usage; reservation retained")
        model = receipt.rsplit(":", 1)[-1]
        if self.command("EVAL", SETTLE, 1, self.key, receipt, token_cost(prompt, completion, model)) != 1:
            raise BudgetUnavailable("Model usage could not be settled; reservation retained")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the durable demo budget; never calls a model")
    parser.add_argument("action", choices=["init", "status", "raise-limit"])
    parser.add_argument("--to", help="New total USD allowance for raise-limit; preserves spent funds")
    args = parser.parse_args()
    if (args.action == "raise-limit") != bool(args.to):
        parser.error("Use --to only with raise-limit, e.g. raise-limit --to 5")
    budget = RemoteBudget()
    if args.action == "init":
        budget.initialize()
    elif args.action == "raise-limit":
        budget.raise_limit(args.to)
    print(json.dumps(budget.status()))


if __name__ == "__main__":
    main()
