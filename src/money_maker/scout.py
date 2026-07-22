from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


GITHUB_API = "https://api.github.com/search/issues"
UNSAFE_TERMS = (
    "arbitrary code execution",
    "aws iam",
    "bleichenbacher",
    "blind xxe",
    "cache poisoning",
    "command injection",
    "captcha",
    "clickjacking",
    "credential",
    "cross-site scripting",
    "cors misconfiguration",
    "dns zone",
    "deserialization",
    "directory traversal",
    "exploit",
    "http request smuggling",
    "idor",
    "injection",
    "ldap",
    "mass assignment",
    "malware",
    "nosql",
    "oracle",
    "password",
    "phishing",
    "private key",
    "prototype pollution",
    "privilege escalation",
    "ransomware",
    "rate limit bypass",
    "remote code execution",
    "race condition",
    "seed phrase",
    "session fixation",
    "security vulnerability",
    "server-side request forgery",
    "ssrf",
    "ssti",
    "timing attack",
    "unauthorized access",
    "vulnerability",
    "xss",
    "xxe",
    "zip slip",
    "data scraping",
    "attacker",
)
_AMOUNT = r"([0-9][0-9,]*(?:\.[0-9]{1,2})?\s*[kK]?)"
REWARD_PATTERNS = (
    re.compile(
        rf"\b(?:bounty|reward)(?:\s+(?:amount|value))?\s*(?:[:=—–-]\s*)?(?:\$|USD\s*|USDC\s*){_AMOUNT}\s*(?:USD|USDC)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:\$|USD\s*|USDC\s*){_AMOUNT}\s*(?:USD|USDC)?\s*(?:bounty|reward)\b",
        re.IGNORECASE,
    ),
)
HOUR_PATTERN = re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:hours?|hrs?)\b", re.IGNORECASE)
SOURCE_URL_PATTERN = re.compile(
    r"(?:source\s+url|original\s+link|原始链接)\s*[:：]?\s*(https?://\S+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Opportunity:
    source_id: str
    title: str
    url: str
    repository: str
    reward_usd: str
    estimated_hours: str
    effective_hourly_usd: str
    risk: str | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def extract_reward(text: str) -> Decimal | None:
    values: list[Decimal] = []
    for pattern in REWARD_PATTERNS:
        for match in pattern.finditer(text):
            try:
                raw = match.group(1).replace(",", "").replace(" ", "")
                multiplier = Decimal("1000") if raw.casefold().endswith("k") else Decimal("1")
                values.append(Decimal(raw.removesuffix("k").removesuffix("K")) * multiplier)
            except InvalidOperation:
                continue
    return max(values) if values else None


def estimate_hours(text: str) -> Decimal:
    matches = [Decimal(match.group(1)) for match in HOUR_PATTERN.finditer(text)]
    return max(matches) if matches else Decimal("4")


def risk_reason(text: str) -> str | None:
    lowered = text.casefold()
    for term in UNSAFE_TERMS:
        if term in lowered:
            return f"unsafe:{term}"
    return None


def payout_risk(issue_url: str, repository: str, body: str) -> str | None:
    """Reject marketplace mirrors until their upstream payout is independently checked.

    A copied reward amount is not proof that a contributor can actually collect it.
    We only flag listings that explicitly identify a different upstream source; ordinary
    issue links in a task description remain eligible for manual review.
    """
    source_match = SOURCE_URL_PATTERN.search(body)
    if source_match is None:
        return None
    source_url = source_match.group(1).rstrip(".,)")
    if source_url != issue_url:
        return "unverified:payout source"
    return None


def normalize_issue(item: dict[str, Any]) -> Opportunity | None:
    if not isinstance(item, dict) or item.get("pull_request") is not None:
        return None
    url = item.get("html_url")
    repository = item.get("repository_url")
    title = item.get("title")
    issue_id = item.get("id")
    user = item.get("user")
    if (
        not isinstance(url, str)
        or not url.startswith("https://github.com/")
        or not isinstance(repository, str)
        or not repository.startswith("https://api.github.com/repos/")
        or not isinstance(title, str)
        or not isinstance(issue_id, int)
        or not isinstance(user, dict)
        or not isinstance(user.get("login"), str)
    ):
        return None
    body = item.get("body") if isinstance(item.get("body"), str) else ""
    text = f"{title}\n{body}"
    reward = extract_reward(text)
    if reward is None or reward <= 0:
        return None
    hours = estimate_hours(text)
    risk = risk_reason(text) or payout_risk(url, repository, body)
    reason = "explicit reward evidence"
    if risk is not None:
        reason = f"rejected: {risk}"
    hourly = reward / hours if hours > 0 else Decimal("0")
    return Opportunity(
        source_id=f"github:{issue_id}",
        title=title[:300],
        url=url,
        repository=repository.removeprefix("https://api.github.com/repos/"),
        reward_usd=f"{reward:.2f}",
        estimated_hours=f"{hours:.2f}",
        effective_hourly_usd=f"{hourly:.2f}",
        risk=risk,
        reason=reason,
    )


def rank(opportunities: list[Opportunity]) -> list[Opportunity]:
    return sorted(
        opportunities,
        key=lambda item: (
            item.risk is None,
            Decimal(item.effective_hourly_usd),
            Decimal(item.reward_usd),
        ),
        reverse=True,
    )


def eligible(opportunities: list[Opportunity]) -> list[Opportunity]:
    """Return only opportunities that have no detected safety or payout risk."""
    return [opportunity for opportunity in opportunities if opportunity.risk is None]


def scan_github(query: str = "(bounty OR reward) state:open", timeout: int = 15) -> list[Opportunity]:
    if not query.strip() or len(query) > 300:
        raise ValueError("query must be between 1 and 300 characters")
    if timeout < 1:
        raise ValueError("timeout must be positive")
    url = f"{GITHUB_API}?{urllib.parse.urlencode({'q': query, 'per_page': 50})}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "money-maker-readonly/0.1"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("GitHub returned an invalid search envelope")
    return rank([item for raw in payload["items"] if (item := normalize_issue(raw)) is not None])
