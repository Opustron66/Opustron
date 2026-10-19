"""Serve the egress log to the UI: ``python -m chronicle.guard.egress_server``.

Only ``GET /api/egress?n=30`` (newest first). Binds to 127.0.0.1 so the log is
never reachable from other machines. Runs on its own port (default 8001) so it
can sit beside whatever serves the rest of ``/api``.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .egress_logger import EgressLogger, get_logger

DEFAULT_PORT = 8001
DEFAULT_N = 30
MAX_N = 500


def make_server(port: int = DEFAULT_PORT, logger: EgressLogger | None = None) -> ThreadingHTTPServer:
    source = logger or get_logger()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            url = urlsplit(self.path)
            if url.path != "/api/egress":
                self._send(404, {"error": "not found"})
                return
            try:
                n = int(parse_qs(url.query).get("n", [DEFAULT_N])[0])
            except ValueError:
                self._send(400, {"error": "n must be an integer"})
                return
            self._send(200, source.tail(max(1, min(n, MAX_N))))

        def _send(self, status: int, body: object) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass  # the UI polls every 2s; per-request access logs are noise

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="chronicle.guard.egress_server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    server = make_server(args.port)
    print(f"[chronicle] egress log at http://127.0.0.1:{args.port}/api/egress (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
