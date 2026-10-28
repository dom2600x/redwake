"""An ephemeral loopback-only lab. All records and credentials are synthetic."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contracts import RESOURCES, resources_for, discovery_layout, navigation_for
from .guidance import discovery_scenario


ACTORS = {"alice": "lab-alice", "bob": "lab-bob"}

MODES = ("vulnerable", "fixed", "concealed", "broken")


@contextmanager
def lab(mode="fixed", scenario="classic"):
    if mode not in MODES:
        raise ValueError("Unknown lab mode")

    resources = resources_for(scenario)
    layout = discovery_layout(scenario if discovery_scenario(scenario) else "discovery")
    projects = layout["projects"]
    record_paths = list(resources)
    navigation = navigation_for(scenario) if discovery_scenario(scenario) else {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            actor = next((a for a, token in ACTORS.items()
                          if self.headers.get("Authorization") == "Bearer " + token), None)
            record = resources.get(self.path)
            behaviour = record.get("behaviour", mode) if record else mode
            if actor is None:
                status, body = 401, {"error": "unauthenticated"}
            elif discovery_scenario(scenario) and (self.path in navigation or self.path == "/api/projects"):
                if mode == "broken":
                    status, body = 503, {"error": "unavailable"}
                elif self.path == "/api/projects":
                    status, body = 200, {"projects": [{"id": projects[actor], "links": {
                        "self": "/api/projects/" + projects[actor]}}]}
                elif navigation[self.path]['actor'] != actor:
                    status, body = 404, {"error": "not found"}
                else:
                    status, body = 200, navigation[self.path]['body']
            elif record is None:
                status, body = 404, {"error": "not found"}
            elif mode == "broken" or behaviour == "broken":
                status, body = 503, {"error": "unavailable"}
            elif record["private"] and actor != record["owner"] and (mode != "vulnerable" or behaviour != "vulnerable"):
                status = 404 if mode == "concealed" or behaviour == "concealed" else 403
                body = {"error": "denied"}
            else:
                status, body = 200, {"owner": record["owner"], "data": record["marker"]}
                if discovery_scenario(scenario):
                    body["visibility"] = "private" if record["private"] else "public"
                    if self.path == record_paths[0]:
                        body["links"] = {"attachment": record_paths[1]}
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


def allowed_paths(scenario="classic"):
    paths = set(resources_for(scenario))
    if discovery_scenario(scenario):
        paths.add("/api/projects")
        paths.update(navigation_for(scenario))
    return paths
