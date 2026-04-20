"""
Tests for the date+address fuzzy join between private contacts and the
Chicago Data Portal API crash records.

The live API does not expose rd_no, so an exact key join is not possible.
These tests verify that the fuzzy matcher correctly identifies crash records
by date and address prefix.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.fuzzy_join import (
    _addresses_match,
    _build_crash_address,
    _dates_match,
    fuzzy_join,
)
from src.providers.chicago_crashes import ChicagoCrashesProvider

# ---------------------------------------------------------------------------
# Sample data mirroring prototype/data/contacts.json
# ---------------------------------------------------------------------------

CONTACTS = [
    {
        "crash_join_id": "JG299982",
        "date": "2023-06-13",
        "address": "1732 N LA SALLE",
        "unit1_name": "UNKNOWN, UNKNOWN",
        "unit1_phone": None,
        "unit1_insurance": None,
    },
    {
        "crash_join_id": "JG300353",
        "date": "2023-06-14",
        "address": "499 N COLUMBL",
        "unit1_name": "GERK, BRIDGET M",
        "unit1_phone": "7735022152",
        "unit1_insurance": "STATE FARM",
    },
    {
        "crash_join_id": "JG300386",
        "date": "2023-06-14",
        "address": "3311 W PETERS",
        "unit1_name": "WHAM, ALEXANDRA RAE",
        "unit1_phone": "8475081827",
        "unit1_insurance": "GEICO",
    },
]

# Simulated API crash records matching the contacts above
API_CRASHES = [
    {
        "crash_record_id": "HASH_A",
        "crash_date": "2023-06-13T08:15:00.000",
        "street_no": "1732",
        "street_direction": "N",
        "street_name": "LA SALLE DR",
    },
    {
        "crash_record_id": "HASH_B",
        "crash_date": "2023-06-14T14:30:00.000",
        "street_no": "499",
        "street_direction": "N",
        "street_name": "COLUMBUS DR",
    },
    {
        "crash_record_id": "HASH_C",
        "crash_date": "2023-06-14T09:00:00.000",
        "street_no": "3311",
        "street_direction": "W",
        "street_name": "PETERSON AVE",
    },
    # Decoy — wrong date
    {
        "crash_record_id": "HASH_DECOY",
        "crash_date": "2023-06-15T00:00:00.000",
        "street_no": "1732",
        "street_direction": "N",
        "street_name": "LA SALLE DR",
    },
]


# ---------------------------------------------------------------------------
# Unit tests: address helpers
# ---------------------------------------------------------------------------


def test_build_crash_address():
    crash = {"street_no": "1732", "street_direction": "N", "street_name": "LA SALLE DR"}
    assert _build_crash_address(crash) == "1732 N LA SALLE DR"


def test_build_crash_address_missing_fields():
    assert _build_crash_address({}) == ""


def test_addresses_match_prefix():
    # Contact address is a truncated prefix of the API address
    assert _addresses_match("1732 N LA SALLE", "1732 N LA SALLE DR") is True


def test_addresses_match_exact():
    assert _addresses_match("3311 W PETERSON AVE", "3311 W PETERSON AVE") is True


def test_addresses_no_match():
    assert _addresses_match("1732 N LA SALLE", "499 N COLUMBUS DR") is False


def test_addresses_match_none():
    assert _addresses_match(None, "1732 N LA SALLE DR") is False


def test_dates_match_with_time():
    assert _dates_match("2023-06-13", "2023-06-13T08:15:00.000") is True


def test_dates_no_match():
    assert _dates_match("2023-06-13", "2023-06-14T08:15:00.000") is False


def test_dates_match_none():
    assert _dates_match(None, "2023-06-13T08:15:00.000") is False


# ---------------------------------------------------------------------------
# Unit tests: fuzzy_join
# ---------------------------------------------------------------------------


def test_fuzzy_join_matches_all_contacts():
    results = fuzzy_join(CONTACTS, API_CRASHES)
    matched = [r for r in results if r["match_status"] == "matched"]
    assert len(matched) == 3


def test_fuzzy_join_assigns_correct_crash_record_id():
    results = fuzzy_join(CONTACTS, API_CRASHES)
    by_rd = {r["crash_join_id"]: r for r in results}

    assert by_rd["JG299982"]["matched_crash_record_id"] == "HASH_A"
    assert by_rd["JG300353"]["matched_crash_record_id"] == "HASH_B"
    assert by_rd["JG300386"]["matched_crash_record_id"] == "HASH_C"


def test_fuzzy_join_unmatched_contact():
    unmatched_contact = [
        {"crash_join_id": "JG000000", "date": "2000-01-01", "address": "1 W NOWHERE"}
    ]
    results = fuzzy_join(unmatched_contact, API_CRASHES)
    assert results[0]["match_status"] == "unmatched"
    assert results[0]["matched_crash_record_id"] is None


def test_fuzzy_join_decoy_not_matched_to_wrong_date():
    # JG299982 should match HASH_A (2023-06-13), not HASH_DECOY (2023-06-15)
    results = fuzzy_join(CONTACTS[:1], API_CRASHES)
    assert results[0]["matched_crash_record_id"] == "HASH_A"


def test_fuzzy_join_preserves_contact_fields():
    results = fuzzy_join(CONTACTS, API_CRASHES)
    row = next(r for r in results if r["crash_join_id"] == "JG300353")
    assert row["unit1_name"] == "GERK, BRIDGET M"
    assert row["unit1_phone"] == "7735022152"


# ---------------------------------------------------------------------------
# Integration test: mocked live API
# ---------------------------------------------------------------------------


def test_fuzzy_join_with_mocked_api_response():
    """
    Simulates fetching from the live Chicago Data Portal and verifies
    that fuzzy_join resolves the RD-number contacts to crash_record_ids
    using the date+address fallback strategy.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = API_CRASHES

    with patch("requests.get", return_value=mock_response):
        provider = ChicagoCrashesProvider()  # csv_path=None → live API path
        raw_crashes = provider.fetch(limit=10)

    results = fuzzy_join(CONTACTS, raw_crashes)
    matched = [r for r in results if r["match_status"] == "matched"]

    # All 3 contacts should resolve to a crash_record_id
    assert len(matched) == 3
    for row in matched:
        assert row["matched_crash_record_id"] is not None
