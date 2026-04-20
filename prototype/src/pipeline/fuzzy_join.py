"""
Fuzzy join between contacts (keyed by RD number + date + address) and
crash records from the Chicago Data Portal API (keyed by crash_record_id).

The live API endpoint does not expose rd_no, so an exact key join is not
possible. This module matches records using date (exact) + address (prefix).
"""

import re
from typing import Any


def _normalize_address(address: str | None) -> str:
    """Lowercase and strip non-alphanumeric characters for loose comparison."""
    if not address:
        return ""
    return re.sub(r"[^a-z0-9 ]", "", address.lower().strip())


def _build_crash_address(crash: dict[str, Any]) -> str:
    """Construct a full address string from API crash fields."""
    parts = [
        crash.get("street_no"),
        crash.get("street_direction"),
        crash.get("street_name"),
    ]
    return " ".join(str(p).strip() for p in parts if p)


def _addresses_match(contact_addr: str | None, crash_addr: str) -> bool:
    """
    Return True if the contact address is a prefix of (or equals) the crash address.

    Contact addresses are often truncated (e.g. "1732 N LA SALLE" vs
    "1732 N LA SALLE DR"), so prefix matching is used.
    """
    a = _normalize_address(contact_addr)
    b = _normalize_address(crash_addr)
    if not a or not b:
        return False
    return b.startswith(a) or a.startswith(b)


def _dates_match(contact_date: str | None, crash_date: str | None) -> bool:
    """Compare date portion only (contact: '2023-06-13', crash: '2023-06-13T...')."""
    if not contact_date or not crash_date:
        return False
    return contact_date.strip()[:10] == crash_date.strip()[:10]


def fuzzy_join(
    contacts: list[dict[str, Any]],
    crashes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Match each contact record to a crash record by date + address.

    Returns a list of merged dicts. Contact fields are included as-is;
    matched crash fields are added with a 'crash_' prefix to avoid
    collisions. Unmatched contacts are included with crash fields absent.
    """
    results: list[dict[str, Any]] = []

    for contact in contacts:
        contact_date = contact.get("date")
        contact_addr = contact.get("address")
        matched_crash: dict[str, Any] | None = None

        for crash in crashes:
            crash_addr = _build_crash_address(crash)
            if _dates_match(contact_date, crash.get("crash_date")) and \
               _addresses_match(contact_addr, crash_addr):
                matched_crash = crash
                break

        merged: dict[str, Any] = dict(contact)
        if matched_crash:
            merged["matched_crash_record_id"] = matched_crash.get("crash_record_id")
            merged["matched_crash_date"] = matched_crash.get("crash_date")
            merged["matched_crash_address"] = _build_crash_address(matched_crash)
            merged["match_status"] = "matched"
        else:
            merged["matched_crash_record_id"] = None
            merged["matched_crash_date"] = None
            merged["matched_crash_address"] = None
            merged["match_status"] = "unmatched"

        results.append(merged)

    return results
