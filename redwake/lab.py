"""An ephemeral loopback-only lab. All records and credentials are synthetic."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contracts import RESOURCES, resources_for


ACTORS = {"alice": "lab-alice", "bob": "lab-bob"}

MODES = ("vulnerable", "fixed", "concealed", "broken")


@contextmanager
def lab(mode="fixed", scenario="classic"):
    if mode not in MODES:
        raise ValueError("Unknown lab mode")

    resources = resources_for(scenario)
    projects = {"alice": "prj_a5", "bob": "prj_b9"}
    collections = {
        "alice": ["/api/records/doc_k4", "/api/records/guide_h6"],
        "bob": ["/api/records/inv_m8", "/api/records/note_q2", "/api/exports/export_z3"],
    }
    navigation = {"/api/projects"}
    for project in projects.values():
        navigation.update({"/api/projects/" + project, "/api/projects/" + project + "/records"})

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            actor = next((a for a, token in ACTORS.items()
                          if self.headers.get("Authorization") == "Bearer " + token), None)
            record = resources.get(self.path)
            behaviour = record.get("behaviour", mode) if record else mode
            if actor is None:
                status, body = 401, {"error": "unauthenticated"}
            elif scenario == "discovery" and self.path in navigation:
                if mode == "broken":
                    status, body = 503, {"error": "unavailable"}
                elif self.path == "/api/projects":
                    status, body = 200, {"projects": [{"id": projects[actor], "links": {
                        "self": "/api/projects/" + projects[actor]}}]}
                elif not self.path.startswith("/api/projects/" + projects[actor]):
                    status, body = 404, {"error": "not found"}
                elif self.path.endswith("/records"):
                    status, body = 200, {"records": [{"links": {"self": path}}
                                                   for path in collections[actor]]}
                else:
                    status, body = 200, {"id": projects[actor], "links": {
                        "records": self.path + "/records"}}
            elif record is None:
                status, body = 404, {"error": "not found"}
            elif mode == "broken" or behaviour == "broken":
                status, body = 503, {"error": "unavailable"}
            elif record["private"] and actor != record["owner"] and (mode != "vulnerable" or behaviour != "vulnerable"):
                status = 404 if mode == "concealed" or behaviour == "concealed" else 403
                body = {"error": "denied"}
            else:
                status, body = 200, {"owner": record["owner"], "data": record["marker"]}
                if scenario == "discovery":
                    body["visibility"] = "private" if record["private"] else "public"
                    if self.path == "/api/records/doc_k4":
                        body["links"] = {"attachment": "/api/files/file_x9"}
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
    if scenario == "discovery":
        paths.add("/api/projects")
        for project in ("prj_a5", "prj_b9"):
            paths.update({"/api/projects/" + project, "/api/projects/" + project + "/records"})
    return paths
