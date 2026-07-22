"""Small dependency-free HTTP adapter for the PatchRelay verifier."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable
from wsgiref.simple_server import make_server

from .scout import verify_listing


StartResponse = Callable[[str, list[tuple[str, str]]], Callable[[bytes], Any]]


def _json(start_response: StartResponse, status: str, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def application(environ: dict[str, Any], start_response: StartResponse) -> list[bytes]:
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    if method == "GET" and path == "/health":
        return _json(start_response, "200 OK", {"service": "patchrelay-verify", "status": "ok"})
    if method != "POST" or path != "/verify":
        return _json(start_response, "404 Not Found", {"error": "not found"})
    try:
        length = int(environ.get("CONTENT_LENGTH", "0"))
        if length < 1 or length > 20_000:
            raise ValueError("request body must be between 1 and 20000 bytes")
        raw = environ["wsgi.input"].read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        result = verify_listing(
            title=str(payload.get("title", "")),
            body=str(payload.get("body", "")),
            issue_url=str(payload.get("issue_url", "")),
            repository=str(payload.get("repository", "")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return _json(start_response, "400 Bad Request", {"error": str(exc)})
    return _json(start_response, "200 OK", result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PatchRelay verification HTTP service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    with make_server(args.host, args.port, application) as server:
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
