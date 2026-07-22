from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scout import eligible, rank, scan_github


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "artifacts" / "opportunities.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="money-maker")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="scan public GitHub reward issues")
    scan.add_argument("--query", default="(bounty OR reward) state:open")
    scan.add_argument("--timeout", type=int, default=15)
    scan.add_argument("--output", default=str(DEFAULT_OUTPUT))
    scan.add_argument(
        "--include-rejected",
        action="store_true",
        help="include opportunities rejected by the safety and payout checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        scanned = rank(scan_github(args.query, args.timeout))
        opportunities = scanned if args.include_rejected else eligible(scanned)
        payload = {
            "source": "GitHub public issue search",
            "read_only": True,
            "count": len(opportunities),
            "rejected_count": len(scanned) - len(opportunities),
            "opportunities": [item.as_dict() for item in opportunities],
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0
    raise AssertionError("unhandled command")
