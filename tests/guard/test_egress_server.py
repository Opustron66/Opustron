import json
import threading
import urllib.error
import urllib.request

import pytest

from chronicle.guard.egress_logger import EgressLogger
from chronicle.guard.egress_server import make_server


@pytest.fixture
def server(tmp_path):
    logger = EgressLogger(tmp_path / "egress.log")
    for i in range(5):
        logger.log(provider="nebius_token_factory", model="m", redacted=bool(i % 2), request_preview=f"call {i}")
    srv = make_server(port=0, logger=logger)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", logger
    srv.shutdown()
    srv.server_close()


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, resp.headers, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, json.loads(exc.read())


def test_returns_newest_entries_first(server):
    base, _ = server
    status, headers, body = _get(f"{base}/api/egress?n=3")
    assert status == 200
    assert headers["Content-Type"] == "application/json"
    assert headers["Cache-Control"] == "no-store"
    assert [e["request_preview"] for e in body] == ["call 4", "call 3", "call 2"]


def test_picks_up_new_calls_without_restart(server):
    base, logger = server
    logger.log(provider="tavily", model="search", redacted=False, request_preview="NVIDIA OpenShell")
    _, _, body = _get(f"{base}/api/egress")
    assert body[0]["provider"] == "tavily"


@pytest.mark.parametrize(("query", "count"), [("", 5), ("?n=0", 1), ("?n=99999", 5)])
def test_n_defaults_and_is_clamped(server, query, count):
    base, _ = server
    assert len(_get(f"{base}/api/egress{query}")[2]) == count


def test_bad_n_and_unknown_paths(server):
    base, _ = server
    assert _get(f"{base}/api/egress?n=lots")[0] == 400
    assert _get(f"{base}/api/facts")[0] == 404


def test_binds_to_localhost_only(tmp_path):
    srv = make_server(port=0, logger=EgressLogger(tmp_path / "egress.log"))
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.server_close()
