"""ETL orchestrator for the Chicago Crashes pipeline.

Flow
----
1. Fetch crash records from the City of Chicago Open Data API.
2. Build the rd_no → crash_record_id mapping for later cross-dataset joins.
3. Load local contact data from ``data/contacts.json``.
4. Merge crash rows with contact records (left-join on ``rd_no``).
5. Write the merged result to ``data/merged_output.json``.

Usage::

    python -m src.pipeline.main
    python -m src.pipeline.main --limit 500
"""

import argparse
import json
import sys
from pathlib import Path

from src.providers.chicago import ChicagoProvider, build_rd_no_map
from src.utils.data_merger import load_contacts, merge_crashes_with_contacts

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_CONTACTS_PATH = _DATA_DIR / "contacts.json"
_OUTPUT_PATH = _DATA_DIR / "merged_output.json"
_DEFAULT_LIMIT = 1000


def run(limit: int = _DEFAULT_LIMIT, output_path: Path = _OUTPUT_PATH) -> int:
    """Execute the full ETL pipeline.

    Args:
        limit: Maximum number of crash rows to fetch from the API.
        output_path: Where to write the merged JSON output.

    Returns:
        Number of merged rows written.
    """
    print(f"[1/4] Fetching up to {limit} crash records from Chicago Open Data …")
    provider = ChicagoProvider()
    crashes = provider.fetch(limit=limit)
    print(f"      → received {len(crashes)} rows")

    print("[2/4] Building rd_no → crash_record_id mapping …")
    rd_map = build_rd_no_map(crashes)
    print(f"      → mapped {len(rd_map)} rd_no values")

    contacts: list = []
    if _CONTACTS_PATH.exists():
        print(f"[3/4] Loading contacts from {_CONTACTS_PATH} …")
        contacts = load_contacts(_CONTACTS_PATH)
        print(f"      → loaded {len(contacts)} contacts")
    else:
        print(f"[3/4] Contacts file not found at {_CONTACTS_PATH}, skipping merge")

    print("[4/4] Merging crash rows with contacts …")
    merged = merge_crashes_with_contacts(crashes, contacts, crash_key="rd_no")
    print(f"      → {len(merged)} merged rows")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, default=str)
    print(f"\nOutput written to: {output_path}")

    return len(merged)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chicago Crashes ETL pipeline")
    parser.add_argument(
        "--limit",
        type=int,
        default=_DEFAULT_LIMIT,
        help="Maximum crash rows to fetch (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_OUTPUT_PATH,
        help="Output JSON path (default: %(default)s)",
    )
    args = parser.parse_args()

    count = run(limit=args.limit, output_path=args.output)
    print(f"\nDone — {count} rows processed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
