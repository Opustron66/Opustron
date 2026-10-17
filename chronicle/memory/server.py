"""HTTP API over the memory store, for the Memory Time Machine UI.

The routes are the "P2 memory store endpoints" in ``ui/src/services/api.js``. ``router(...)``
returns a FastAPI ``APIRouter`` so the reasoning (``/ask``) and egress (``/egress``) routes can be
mounted on the same app; ``create_app`` serves the memory routes alone.

    python -m chronicle.memory serve --state .tmp/chronicle --port 8000
"""

import threading
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query

from .api import CLAIMS_FILE, MemoryAPI
from .models import parse_when


class StateMemory:
    """A ``MemoryAPI`` over a state dir that picks up claims P1 appends while the server runs."""

    def __init__(self, state: str | Path) -> None:
        self.state = Path(state)
        self.api = MemoryAPI.from_state(self.state, sync=False)
        self._mtime: float | None = None
        self._lock = threading.Lock()
        self.refresh()

    def refresh(self) -> MemoryAPI:
        claims = self.state / CLAIMS_FILE
        mtime = claims.stat().st_mtime if claims.is_file() else None
        with self._lock:
            if mtime is not None and mtime != self._mtime:
                self.api.sync_claims_file(claims)
                self._mtime = mtime
        return self.api


def _when(value: str | None, name: str) -> date | datetime | None:
    if value is None:
        return None
    try:
        return parse_when(value)
    except ValueError:
        raise HTTPException(400, f"{name} must be YYYY-MM-DD or an ISO datetime, got {value!r}") from None


def router(memory: MemoryAPI | StateMemory) -> APIRouter:
    get_api = memory.refresh if isinstance(memory, StateMemory) else (lambda: memory)
    routes = APIRouter()

    @routes.get("/entities")
    def entities() -> list[dict[str, Any]]:
        return [e.to_dict() for e in get_api().entities()]

    @routes.get("/entities/{entity_id}/history")
    def entity_history(entity_id: str, known_at: str | None = None) -> dict[str, Any]:
        api = get_api()
        record = api.entity(entity_id)
        if record is None:
            raise HTTPException(404, f"unknown entity {entity_id!r}")
        facts = api.history(record.name, known_at=_when(known_at, "known_at"))
        return {"entity": record.to_dict(), "facts": [f.to_dict() for f in facts]}

    @routes.get("/facts")
    def facts(as_of: str | None = None, known_at: str | None = None, subject: str | None = None,
              predicate: str | None = None) -> list[dict[str, Any]]:
        """Facts true on ``as_of``; every fact (superseded included) when it is omitted."""
        api, known = get_api(), _when(known_at, "known_at")
        if as_of is None:
            found = api.facts(known_at=known, subject=subject, predicate=predicate)
        else:
            found = api.as_of(_when(as_of, "as_of"), known_at=known, subject=subject, predicate=predicate)
        return [f.to_dict() for f in found]

    @routes.get("/facts/{fact_id}/versions")
    def fact_versions(fact_id: str) -> list[dict[str, Any]]:
        versions = get_api().versions(fact_id)
        if not versions:
            raise HTTPException(404, f"unknown fact {fact_id!r}")
        return [f.to_dict() for f in versions]

    @routes.get("/timeline")
    def timeline(start: str, end: str, entity: str | None = None, known_at: str | None = None) -> list[dict[str, Any]]:
        events = get_api().timeline(_when(start, "start"), _when(end, "end"), entity=entity,
                                    known_at=_when(known_at, "known_at"))
        return [e.to_dict() for e in events]

    @routes.get("/search")
    def search(q: str, as_of: str | None = None, known_at: str | None = None,
               k: int = Query(10, ge=1, le=100)) -> list[dict[str, Any]]:
        hits = get_api().search(q, as_of=_when(as_of, "as_of"), known_at=_when(known_at, "known_at"), k=k)
        return [h.to_dict() for h in hits]

    @routes.get("/span")
    def span() -> dict[str, str | None]:
        lo, hi = get_api().span()
        return {"start": lo.isoformat() if lo else None, "end": hi.isoformat() if hi else None}

    return routes


def create_app(memory: MemoryAPI | StateMemory | str | Path) -> FastAPI:
    if isinstance(memory, (str, Path)):
        memory = StateMemory(memory)
    app = FastAPI(title="Chronicle memory")
    app.include_router(router(memory), prefix="/api")
    return app
