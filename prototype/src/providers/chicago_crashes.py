import csv
from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseProvider


class ChicagoCrashesProvider(BaseProvider):
    """Loads public crash rows from the local CSV export."""

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        default_path = Path(__file__).resolve().parents[3] / "chicago_crashes.csv"
        self.csv_path = csv_path or default_path

    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        with self.csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                # Provide a local merge key used by contacts data.
                row["rd"] = row.get("crash_record_id", "")
                rows.append(row)
                if limit and index >= limit:
                    break
        return rows
