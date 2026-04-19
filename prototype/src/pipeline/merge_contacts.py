import csv
from pathlib import Path
from typing import Dict, List


def load_contacts(contacts_csv: Path) -> List[Dict[str, str]]:
    with contacts_csv.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def merge_crashes_with_contacts(
    crashes: List[Dict[str, str]], contacts: List[Dict[str, str]], key: str = "rd"
) -> List[Dict[str, str]]:
    contact_map = {row.get(key, ""): row for row in contacts}

    merged: List[Dict[str, str]] = []
    for crash in crashes:
        merge_key = crash.get(key, "")
        contact = contact_map.get(merge_key, {})
        merged.append({**crash, **contact})
    return merged
