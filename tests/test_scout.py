from __future__ import annotations

import unittest

from money_maker.scout import eligible, extract_reward, normalize_issue, payout_risk, rank, risk_reason


class ScoutTests(unittest.TestCase):
    def test_extracts_highest_explicit_reward(self) -> None:
        self.assertEqual(extract_reward("Reward: $125 USD, bonus 20 USDC"), 125)
        self.assertEqual(extract_reward("[Bounty $4k] Fix the parser"), 4000)
        self.assertIsNone(
            extract_reward("Post a Bounty form is broken. The site reports $8,000 USDC paid out.")
        )

    def test_normalizes_and_ranks_safe_issue(self) -> None:
        issue = normalize_issue(
            {
                "id": 42,
                "title": "Python cleanup bounty $80",
                "body": "Expected effort: 2 hours.",
                "html_url": "https://github.com/example/project/issues/42",
                "repository_url": "https://api.github.com/repos/example/project",
                "user": {"login": "requester"},
            }
        )
        self.assertIsNotNone(issue)
        assert issue is not None
        self.assertEqual(issue.effective_hourly_usd, "40.00")
        self.assertIsNone(issue.risk)

    def test_rejects_pull_requests_and_unsafe_terms(self) -> None:
        pull = {
            "id": 1,
            "title": "Reward $100",
            "body": "",
            "html_url": "https://github.com/example/project/pull/1",
            "repository_url": "https://api.github.com/repos/example/project",
            "user": {"login": "requester"},
            "pull_request": {"url": "https://api.github.com/repos/example/project/pulls/1"},
        }
        self.assertIsNone(normalize_issue(pull))
        self.assertEqual(risk_reason("Need credentials for a $100 task"), "unsafe:credential")
        self.assertIsNone(risk_reason("[Bounty] [BUG] Fix a broken parser for $100"))
        self.assertEqual(risk_reason("Attacker can use a rate limit bypass for data scraping"), "unsafe:rate limit bypass")

    def test_flags_reward_mirrors_until_upstream_payout_is_verified(self) -> None:
        issue = normalize_issue(
            {
                "id": 626,
                "title": "[Bounty] [$337] Mapping bounty",
                "body": (
                    "Source URL: https://github.com/Iamgoofball/-tg-station/issues/109\n"
                    "Real Reward: $337"
                ),
                "html_url": "https://github.com/example/bounty-plaza/issues/626",
                "repository_url": "https://api.github.com/repos/example/bounty-plaza",
                "user": {"login": "requester"},
            }
        )
        self.assertIsNotNone(issue)
        assert issue is not None
        self.assertEqual(issue.risk, "unverified:payout source")
        self.assertEqual(issue.reason, "rejected: unverified:payout source")
        self.assertEqual(
            payout_risk("https://github.com/example/project/issues/1", "example/project", "Reward: $50"),
            None,
        )

    def test_safe_opportunities_rank_before_risky_ones(self) -> None:
        safe = normalize_issue(
            {
                "id": 2,
                "title": "Docs bounty $10",
                "body": "",
                "html_url": "https://github.com/example/project/issues/2",
                "repository_url": "https://api.github.com/repos/example/project",
                "user": {"login": "requester"},
            }
        )
        risky = normalize_issue(
            {
                "id": 3,
                "title": "Exploit bounty $1000",
                "body": "",
                "html_url": "https://github.com/example/project/issues/3",
                "repository_url": "https://api.github.com/repos/example/project",
                "user": {"login": "requester"},
            }
        )
        assert safe is not None and risky is not None
        self.assertEqual(rank([risky, safe])[0].source_id, safe.source_id)
        self.assertEqual(eligible([safe, risky]), [safe])


if __name__ == "__main__":
    unittest.main()
