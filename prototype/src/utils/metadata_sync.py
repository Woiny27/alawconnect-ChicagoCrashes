from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse

import requests


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_csv_rows_from_text(csv_text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(csv_text.splitlines()))


def google_sheet_url_to_csv_export_url(sheet_url: str) -> str:
    """Convert a Google Sheet URL into a CSV export URL.

    Supports URLs like:
    - https://docs.google.com/spreadsheets/d/<sheet_id>/edit?gid=0#gid=0
    - https://docs.google.com/spreadsheets/d/<sheet_id>/edit#gid=123
    """
    parsed = urlparse(sheet_url)
    path_parts = [part for part in parsed.path.split("/") if part]

    if parsed.netloc != "docs.google.com" or len(path_parts) < 3:
        raise ValueError("not a valid Google Sheets URL")

    if path_parts[0] != "spreadsheets" or path_parts[1] != "d":
        raise ValueError("not a valid Google Sheets URL")

    sheet_id = path_parts[2]
    query = parse_qs(parsed.query)
    gid = query.get("gid", [""])[0]

    if not gid and parsed.fragment.startswith("gid="):
        gid = parsed.fragment.split("=", maxsplit=1)[1]

    if gid:
        return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


def _is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def read_metadata_rows(source: str | Path, timeout_seconds: int = 30) -> list[dict[str, str]]:
    """Read metadata rows from either local CSV path or URL.

    When a Google Sheets URL is provided, it is converted to CSV export format.
    """
    source_text = str(source)
    if _is_url(source_text):
        url = source_text
        if "docs.google.com/spreadsheets/" in source_text:
            url = google_sheet_url_to_csv_export_url(source_text)
        response = requests.get(url, timeout=timeout_seconds)
        response.raise_for_status()
        return read_csv_rows_from_text(response.text)

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Metadata source not found: {path}")
    return read_csv_rows(path)


def write_csv_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sync_metadata(
    base_rows: list[dict[str, str]],
    metadata_rows: Iterable[dict[str, str]],
    *,
    key: str = "crash_join_id",
    metadata_fields: list[str] | None = None,
    overwrite: bool = False,
) -> list[dict[str, str]]:
    """Sync metadata fields into base rows using a shared key.

    Rules:
    - Rows are matched by key.
    - If metadata_fields is None, all metadata columns except key are synced.
    - Existing values in base_rows are preserved unless overwrite=True.
    """
    metadata_rows_list = list(metadata_rows)
    metadata_index = {
        row.get(key, ""): row
        for row in metadata_rows_list
        if row.get(key, "")
    }

    if metadata_fields is None:
        fields: list[str] = sorted(
            {
                col
                for row in metadata_rows_list
                for col in row.keys()
                if col != key
            }
        )
    else:
        fields = [field for field in metadata_fields if field != key]

    synced: list[dict[str, str]] = []
    for row in base_rows:
        out = dict(row)
        match = metadata_index.get(row.get(key, ""))
        if not match:
            synced.append(out)
            continue

        for field in fields:
            incoming = match.get(field)
            if incoming in (None, ""):
                continue

            current = out.get(field)
            if overwrite or current in (None, ""):
                out[field] = incoming

        synced.append(out)

    return synced


def run(
    base_csv: Path,
    metadata_source: str | Path,
    *,
    output_csv: Path | None = None,
    key: str = "crash_join_id",
    metadata_fields: list[str] | None = None,
    overwrite: bool = False,
) -> Path:
    base_rows = read_csv_rows(base_csv)
    metadata_rows = read_metadata_rows(metadata_source)

    synced = sync_metadata(
        base_rows,
        metadata_rows,
        key=key,
        metadata_fields=metadata_fields,
        overwrite=overwrite,
    )

    out_path = output_csv or base_csv
    write_csv_rows(out_path, synced)
    return out_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync metadata columns into a base CSV")
    parser.add_argument("base_csv", type=Path, help="Base CSV path")
    parser.add_argument(
        "metadata_source",
        help="Metadata CSV path or URL (Google Sheets links supported)",
    )
    parser.add_argument("--output", type=Path, default=None, help="Output CSV path")
    parser.add_argument("--key", default="crash_join_id", help="Join key column")
    parser.add_argument(
        "--fields",
        default=None,
        help="Comma-separated metadata fields to sync (default: all fields)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing non-empty values in the base CSV",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    fields = None
    if args.fields:
        fields = [field.strip() for field in args.fields.split(",") if field.strip()]

    out = run(
        args.base_csv,
        args.metadata_source,
        output_csv=args.output,
        key=args.key,
        metadata_fields=fields,
        overwrite=args.overwrite,
    )
    print(f"Metadata sync complete: {out}")


if __name__ == "__main__":
    main()