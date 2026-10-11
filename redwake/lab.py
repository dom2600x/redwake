"""An ephemeral loopback-only lab. All records and credentials are synthetic."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


ACTORS = {"alice": "lab-alice", "bob": "lab-bob"}
RESOURCES = {
    "/api/documents/101": {"owner": "alice", "private": True, "marker": "alice-private-document"},
    "/api/invoices/inv_b7": {"owner": "bob", "private": True, "marker": "bob-private-invoice"},
    "/api/documents/public": {"owner": "alice", "private": False, "marker": "public-handbook"},
}
MODES = ("vulnerable", "fixed", "concealed", "broken")


@contextmanager
def lab(mode="fixed"):
    if mode not in MODES:
        raise ValueError("Unknown lab mode")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            actor = next((a for a, token in ACTORS.items()
                          if self.headers.get("Authorization") == "Bearer " + token), None)
            record = RESOURCES.get(self.path)
            if actor is None:
                status, body = 401, {"error": "unauthenticated"}
            elif record is None:
                status, body = 404, {"error": "not found"}
            elif mode == "broken":
                status, body = 503, {"error": "unavailable"}
            elif record["private"] and actor != record["owner"] and mode != "vulnerable":
                status = 404 if mode == "concealed" else 403
                body = {"error": "denied"}
            else:
                status, body = 200, {"owner": record["owner"], "data": record["marker"]}
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
