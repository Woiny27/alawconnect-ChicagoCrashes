import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_contacts(contacts_json: Path) -> List[Dict[str, Any]]:
    """Load contacts from a JSON file.

    Args:
        contacts_json: Path to a JSON file containing a list of contact dicts.

    Returns:
        List of contact dicts.
    """
    with contacts_json.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def merge_crashes_with_contacts(
    crashes: List[Dict[str, Any]],
    contacts: List[Dict[str, Any]],
    crash_key: str = "rd_no",
    contact_key: str = "rd_no",
) -> List[Dict[str, Any]]:
    """Left-join crash rows with contact records on a shared key.

    Each crash row is augmented with any matching contact fields.  Crashes with
    no matching contact are returned unchanged.  Contact fields whose names
    collide with crash fields are prefixed with ``contact_`` to avoid silent
    overwrites.

    Args:
        crashes: Raw crash rows (e.g. from :class:`ChicagoProvider`).
        contacts: Contact records loaded from ``data/contacts.json``.
        crash_key: Field name in *crashes* to join on (default ``rd_no``).
        contact_key: Field name in *contacts* to join on (default ``rd_no``).

    Returns:
        A new list of merged dicts, one per crash row.
    """
    contact_map: Dict[str, Dict[str, Any]] = {
        str(row.get(contact_key, "")): row for row in contacts
    }

    merged: List[Dict[str, Any]] = []
    for crash in crashes:
        key_value = str(crash.get(crash_key, ""))
        contact = contact_map.get(key_value, {})

        # Prefix colliding contact fields to preserve crash data integrity.
        safe_contact: Dict[str, Any] = {}
        for field, value in contact.items():
            if field == contact_key:
                continue  # already present in the crash row
            out_field = f"contact_{field}" if field in crash else field
            safe_contact[out_field] = value

        merged.append({**crash, **safe_contact})

    return merged
