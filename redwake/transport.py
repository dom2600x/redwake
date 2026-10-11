"""Bounded HTTP with no redirects or environment proxy inheritance."""

import json
import time
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, headers=None, payload=None, timeout=10, limit=65536):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(url, data=data, headers=headers or {})
    started = time.monotonic()
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Response exceeds size limit")
        # Socket timeouts bound blocking I/O; this also rejects late responses.
        if time.monotonic() - started > timeout:
            raise TimeoutError("Response exceeded time allowance")
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            body = {"error": "non-JSON response"}
        return response.code, body


def probe(origin, actor, path, timeout=10):
    from .lab import ACTORS, RESOURCES
    from urllib.parse import urlsplit

    parsed = urlsplit(origin)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
            or parsed.username or parsed.password or parsed.path
            or parsed.query or parsed.fragment or not parsed.port):
        raise ValueError("Only the exact loopback lab origin is supported")
    if actor not in ACTORS or path not in RESOURCES:
        raise ValueError("Actor or path outside the lab contract")
    status, body = request_json(origin + path,
                                {"Authorization": "Bearer " + ACTORS[actor]}, timeout=timeout)
    return {"actor": actor, "path": path, "status": status, "body": body}
