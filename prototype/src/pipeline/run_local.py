import csv
from pathlib import Path

from src.pipeline.merge_contacts import load_contacts, merge_crashes_with_contacts
from src.providers.chicago_crashes import ChicagoCrashesProvider


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    fieldnames = sorted({k for row in rows for k in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    provider = ChicagoCrashesProvider()

    crashes = provider.fetch(limit=200)
    contacts_path = root / "data" / "contacts_template.csv"
    contacts = load_contacts(contacts_path) if contacts_path.exists() else []

    merged = merge_crashes_with_contacts(crashes, contacts, key="rd")

    out_path = root / "data" / "merged_output.csv"
    write_csv(out_path, merged)
    print(f"Merged rows: {len(merged)}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
