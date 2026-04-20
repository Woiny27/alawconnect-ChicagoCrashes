"""Tests for src/utils/metadata_sync.py."""

from __future__ import annotations

import pytest

from src.utils.metadata_sync import (
    _build_export_url,
    _resolve_id_column,
    fetch_sheet_df,
    fetch_target_ids,
)

import pandas as pd


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _StubSession:
    """Minimal stand-in for requests.Session."""

    def __init__(self, response: _StubResponse):
        self._response = response
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self._response


CSV_WITH_CRASH_RECORD_ID = """\
crash_record_id,crash_date,address
abc123,2026-04-18,123 Main St
def456,2026-04-17,456 Oak Ave
abc123,2026-04-16,789 Pine Rd
"""

CSV_WITH_RD = """\
rd,name
RD001,Alice
RD002,Bob
"""

CSV_UNKNOWN_COLUMNS = """\
ticket_id,amount
T1,100
T2,200
"""

CSV_EMPTY_ROWS = """\
crash_record_id,notes
abc123,first
,missing id
  ,whitespace only
def456,last
"""


# ---------------------------------------------------------------------------
# _build_export_url
# ---------------------------------------------------------------------------

def test_build_export_url_contains_sheet_id():
    url = _build_export_url("SHEET_ID", "0")
    assert "SHEET_ID" in url


def test_build_export_url_contains_csv_format():
    url = _build_export_url("SHEET_ID", "0")
    assert "format=csv" in url


def test_build_export_url_contains_gid():
    url = _build_export_url("SHEET_ID", "42")
    assert "gid=42" in url


# ---------------------------------------------------------------------------
# fetch_sheet_df
# ---------------------------------------------------------------------------

def test_fetch_sheet_df_returns_dataframe():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    df = fetch_sheet_df(session=session)
    assert isinstance(df, pd.DataFrame)


def test_fetch_sheet_df_row_count():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    df = fetch_sheet_df(session=session)
    assert len(df) == 3


def test_fetch_sheet_df_columns():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    df = fetch_sheet_df(session=session)
    assert "crash_record_id" in df.columns


def test_fetch_sheet_df_raises_on_http_error():
    session = _StubSession(_StubResponse("error", status_code=404))
    with pytest.raises(RuntimeError):
        fetch_sheet_df(session=session)


def test_fetch_sheet_df_raises_on_bad_csv():
    # Provide completely empty text so pandas has nothing to parse
    session = _StubSession(_StubResponse(""))
    # pandas can parse empty strings as an empty DataFrame, so check that
    # a truly unparseable payload raises ValueError.
    # We simulate a non-CSV payload that triggers the ValueError branch by
    # monkeypatching pd.read_csv temporarily.
    import src.utils.metadata_sync as mod
    original = mod.pd.read_csv

    def _bad_read_csv(*args, **kwargs):
        raise Exception("simulated parse error")

    mod.pd.read_csv = _bad_read_csv
    try:
        with pytest.raises(ValueError, match="Failed to parse"):
            fetch_sheet_df(session=session)
    finally:
        mod.pd.read_csv = original


def test_fetch_sheet_df_passes_url_to_session():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    fetch_sheet_df(sheet_id="MY_ID", gid="5", session=session)
    assert "MY_ID" in session.calls[0]["url"]
    assert "gid=5" in session.calls[0]["url"]


# ---------------------------------------------------------------------------
# _resolve_id_column
# ---------------------------------------------------------------------------

def test_resolve_id_column_explicit():
    df = pd.DataFrame({"rd": ["a"], "other": ["b"]})
    assert _resolve_id_column(df, "rd") == "rd"


def test_resolve_id_column_explicit_missing_raises():
    df = pd.DataFrame({"other": ["b"]})
    with pytest.raises(KeyError):
        _resolve_id_column(df, "crash_record_id")


def test_resolve_id_column_auto_crash_record_id():
    df = pd.DataFrame({"crash_record_id": ["x"], "extra": [1]})
    assert _resolve_id_column(df, None) == "crash_record_id"


def test_resolve_id_column_auto_rd():
    df = pd.DataFrame({"rd": ["x"], "extra": [1]})
    assert _resolve_id_column(df, None) == "rd"


def test_resolve_id_column_auto_fallback_to_first():
    df = pd.DataFrame({"ticket_id": ["x"], "amount": [1]})
    assert _resolve_id_column(df, None) == "ticket_id"


def test_resolve_id_column_empty_df_raises():
    df = pd.DataFrame()
    with pytest.raises(KeyError):
        _resolve_id_column(df, None)


# ---------------------------------------------------------------------------
# fetch_target_ids
# ---------------------------------------------------------------------------

def test_fetch_target_ids_deduplicates():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    ids = fetch_target_ids(session=session)
    assert ids.count("abc123") == 1


def test_fetch_target_ids_returns_list():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    ids = fetch_target_ids(session=session)
    assert isinstance(ids, list)


def test_fetch_target_ids_count():
    session = _StubSession(_StubResponse(CSV_WITH_CRASH_RECORD_ID))
    ids = fetch_target_ids(session=session)
    # 3 rows but one duplicate → 2 unique IDs
    assert len(ids) == 2


def test_fetch_target_ids_with_rd_column():
    session = _StubSession(_StubResponse(CSV_WITH_RD))
    ids = fetch_target_ids(session=session)
    assert ids == ["RD001", "RD002"]


def test_fetch_target_ids_explicit_column():
    session = _StubSession(_StubResponse(CSV_UNKNOWN_COLUMNS))
    ids = fetch_target_ids(id_column="ticket_id", session=session)
    assert ids == ["T1", "T2"]


def test_fetch_target_ids_filters_empty_strings():
    session = _StubSession(_StubResponse(CSV_EMPTY_ROWS))
    ids = fetch_target_ids(session=session)
    # Only "abc123" and "def456" should survive; blank / whitespace-only rows dropped
    assert "" not in ids
    assert "abc123" in ids
    assert "def456" in ids


def test_fetch_target_ids_filters_whitespace_only():
    session = _StubSession(_StubResponse(CSV_EMPTY_ROWS))
    ids = fetch_target_ids(session=session)
    for id_ in ids:
        assert id_.strip() == id_
        assert id_ != ""
