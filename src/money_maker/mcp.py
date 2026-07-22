"""A dependency-free MCP server for assessing public bounty listings over stdio."""

from __future__ import annotations

import json
import sys
from typing import Any

from .scout import verify_listing


TOOL = {
    "name": "verify_public_bounty",
    "description": "Assess a public software-work listing for explicit reward evidence, unsafe scope, and copied payout claims.",
    "inputSchema": {
        "type": "object",
        "required": ["title", "issue_url", "repository"],
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string", "default": ""},
            "issue_url": {"type": "string", "format": "uri"},
            "repository": {"type": "string"},
        },
    },
}


def response(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle(request: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request; notifications intentionally receive no response."""
    request_id = request.get("id")
    method = request.get("method")
    if not isinstance(method, str):
        return error(request_id, -32600, "method must be a string")
    if method == "initialize":
        return response(
            request_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "patchrelay-verify", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return response(request_id, {"tools": [TOOL]})
    if method == "tools/call":
        params = request.get("params")
        if not isinstance(params, dict) or params.get("name") != TOOL["name"]:
            return error(request_id, -32602, "unknown tool")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return error(request_id, -32602, "arguments must be an object")
        try:
            result = verify_listing(
                title=str(arguments.get("title", "")),
                body=str(arguments.get("body", "")),
                issue_url=str(arguments.get("issue_url", "")),
                repository=str(arguments.get("repository", "")),
            )
        except ValueError as exc:
            return error(request_id, -32602, str(exc))
        return response(
            request_id,
            {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}], "structuredContent": result},
        )
    if request_id is None:
        return None
    return error(request_id, -32601, "method not found")


def main() -> int:
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be an object")
            result = handle(request)
        except (json.JSONDecodeError, ValueError) as exc:
            result = error(None, -32700, str(exc))
        if result is not None:
            print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
