from __future__ import annotations

import io
import json
import unittest

from money_maker.http_api import application


class HttpApiTests(unittest.TestCase):
    def call(self, method: str, path: str, body: bytes = b"") -> tuple[str, dict[str, object]]:
        received: dict[str, str] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            received["status"] = status
            received["headers"] = str(headers)

        response = application(
            {
                "REQUEST_METHOD": method,
                "PATH_INFO": path,
                "CONTENT_LENGTH": str(len(body)),
                "wsgi.input": io.BytesIO(body),
            },
            start_response,
        )
        return received["status"], json.loads(b"".join(response).decode("utf-8"))

    def test_health_endpoint(self) -> None:
        status, payload = self.call("GET", "/health")
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload["status"], "ok")

    def test_verifies_listing(self) -> None:
        body = json.dumps(
            {
                "title": "Documentation repair for $125 bounty",
                "issue_url": "https://github.com/example/project/issues/1",
                "repository": "example/project",
            }
        ).encode()
        status, payload = self.call("POST", "/verify", body)
        self.assertEqual(status, "200 OK")
        self.assertTrue(payload["eligible"])

    def test_rejects_bad_request(self) -> None:
        status, payload = self.call("POST", "/verify", b"not json")
        self.assertEqual(status, "400 Bad Request")
        self.assertIn("error", payload)
