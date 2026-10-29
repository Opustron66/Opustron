"""Hosted UI and API: ``python -m chronicle.web`` (no ingestion on startup)."""

import asyncio
import math
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from chronicle.guard.egress_logger import get_logger
from chronicle.guard.state_snapshot import restore_snapshot
from chronicle.memory import MemoryAPI
from chronicle.memory.server import router


def create_app() -> FastAPI:
    """Single-process public demo over an approved synthetic memory state."""
    static = Path(os.environ.get("CHRONICLE_WEB_STATIC_DIR", Path(__file__).resolve().parents[1] / "ui/dist"))
    if not (static / "index.html").is_file():
        raise ValueError("Build the UI with npm run build, or set CHRONICLE_WEB_STATIC_DIR")
    chat = os.environ.get("CHRONICLE_WEB_CHAT_ENABLED", "0").lower() in {"1", "true", "yes", "on"}
    ephemeral = os.environ.get("CHRONICLE_WEB_EPHEMERAL", "0").lower() in {"1", "true", "yes", "on"}
    if ephemeral and chat:
        raise ValueError("Paid chat is disabled on ephemeral hosting because spending logs reset on restart")
    limit = int(os.environ.get("CHRONICLE_WEB_ASKS_PER_MINUTE", "6"))
    if limit < 1:
        raise ValueError("CHRONICLE_WEB_ASKS_PER_MINUTE must be positive")
    if chat:
        cap = float(os.environ.get("CHRONICLE_SPEND_LIMIT_USD", "0"))
        if not math.isfinite(cap) or cap <= 0:
            raise ValueError("Set a positive CHRONICLE_SPEND_LIMIT_USD before enabling chat")
        if not (os.environ.get("NEBIUS_API_KEY") or os.environ.get("OPENAI_API_KEY")):
            raise ValueError("Configure a model API key before enabling chat")

    state = Path(os.environ.get("CHRONICLE_STATE_DIR", "data/hosted-state"))
    snapshot_url = os.environ.get("CHRONICLE_STATE_SNAPSHOT_URL", "")
    snapshot_sha = os.environ.get("CHRONICLE_STATE_SNAPSHOT_SHA256", "")
    if snapshot_url or snapshot_sha:
        state = restore_snapshot(state, snapshot_url, snapshot_sha)
    memory = MemoryAPI.from_state(state)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            memory.close()

    app = FastAPI(title="Chronicle", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    ask_lock = asyncio.Lock()
    asks: deque[float] = deque()

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if request.url.path == "/healthz" and request.method in {"GET", "HEAD"}:
            return await call_next(request)
        if request.method == "POST" and request.url.path.rstrip("/") == "/api/ask":
            if not chat:
                return JSONResponse({"detail": "Chat is disabled. Saved memory is available to browse."},
                                    status_code=503, headers={"Cache-Control": "no-store"})
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site chat requests are not allowed"}, status_code=403)
            now = time.monotonic()
            while asks and asks[0] <= now - 60:
                asks.popleft()
            if len(asks) >= limit or ask_lock.locked():
                return JSONResponse({"detail": "Chat is busy. Please try again shortly."}, status_code=429,
                                    headers={"Retry-After": "60", "Cache-Control": "no-store"})
            async with ask_lock:
                asks.append(now)
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok", "memory_loaded": bool(memory.database.query("SELECT 1 FROM facts LIMIT 1"))}

    @app.get("/api/egress")
    def egress(n: int = 30):
        return get_logger().tail(max(1, min(n, 500)))

    app.include_router(router(memory), prefix="/api")
    app.mount("/", StaticFiles(directory=static, html=True), name="ui")
    return app


def main() -> None:
    import uvicorn

    # One worker: a shared SQLite store and one global chat limit for this demo.
    uvicorn.run(create_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")),
                workers=1, proxy_headers=True, forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"))


if __name__ == "__main__":
    main()
