import argparse
import json
import sys
from typing import Any, Dict, List

from src.providers.legacy_portal_provider import LegacyPortalProvider


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run legacy portal lookup using a profile from jurisdictions.yaml",
    )
    parser.add_argument(
        "profile_key",
        help="Profile key under jurisdictions.* (for example: pennsylvania_state_psp)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of accident IDs to check",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    return parser


def run(profile_key: str, limit: int | None, pretty: bool) -> List[Dict[str, Any]]:
    provider = LegacyPortalProvider.from_profile(profile_key)
    rows = provider.fetch(limit=limit)
    if pretty:
        print(json.dumps(rows, indent=2, ensure_ascii=True))
    else:
        print(json.dumps(rows, ensure_ascii=True))
    return rows


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        run(profile_key=args.profile_key, limit=args.limit, pretty=args.pretty)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
