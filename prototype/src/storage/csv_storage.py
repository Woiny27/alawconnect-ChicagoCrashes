import csv
from pathlib import Path
from typing import Any

from .base import BaseStorage


class CsvStorage(BaseStorage):
    """Persist records to a CSV file for local runs."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path

    def upsert(self, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = sorted({key for record in records for key in record.keys()})

        with self.output_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        return len(records)