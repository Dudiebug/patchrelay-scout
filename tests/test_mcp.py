from __future__ import annotations

import json
import unittest

from money_maker.mcp import handle


class McpTests(unittest.TestCase):
    def test_lists_verification_tool(self) -> None:
        result = handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert result is not None
        self.assertEqual(result["result"]["tools"][0]["name"], "verify_public_bounty")

    def test_calls_verification_tool(self) -> None:
        result = handle(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "verify_public_bounty",
                    "arguments": {
                        "title": "Repair docs — $100 bounty",
                        "issue_url": "https://github.com/example/project/issues/1",
                        "repository": "example/project",
                    },
                },
            }
        )
        assert result is not None
        payload = json.loads(result["result"]["content"][0]["text"])
        self.assertTrue(payload["eligible"])
