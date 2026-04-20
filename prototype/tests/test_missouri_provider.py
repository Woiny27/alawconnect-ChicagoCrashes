"""Tests for MissouriProvider — MSHP Troop portal lookup."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.providers.missouri_provider import MissouriProvider, TROOP_COVERAGE


# ---------------------------------------------------------------------------
# Construction / configuration
# ---------------------------------------------------------------------------

class TestMissouriProviderInit:
    def test_defaults(self):
        p = MissouriProvider()
        assert p.troop == "C"
        assert p.source == "mshp_troop_c"
        assert "Troop C" in p.agency

    def test_custom_troop(self):
        p = MissouriProvider(troop="e")
        assert p.troop == "E"
        assert p.source == "mshp_troop_e"
        assert "Troop E" in p.agency

    def test_accident_ids_stored(self):
        p = MissouriProvider(accident_ids=["250111396", "  ", "250201258"])
        assert p.default_ids == ["250111396", "250201258"]

    def test_troop_coverage_keys(self):
        assert "C" in TROOP_COVERAGE
        assert "E" in TROOP_COVERAGE


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------

NOT_FOUND_HTML = "<html><body>No records found for that accident number.</body></html>"

RESULT_HTML = """
<html><body>
  <table>
    <tr><th>Report Date</th><td>2025-01-11</td></tr>
    <tr><th>County</th><td>New Madrid</td></tr>
    <tr><th>Location</th><td>US-61 at Milepost 14</td></tr>
    <tr><th>Troop</th><td>E</td></tr>
  </table>
  <p>Driver: John Doe involved in crash.</p>
</body></html>
"""


class TestNormalize:
    def setup_method(self):
        self.p = MissouriProvider(troop="E")

    def test_not_found_returns_none(self):
        assert self.p.normalize(NOT_FOUND_HTML, "250111396") is None

    def test_found_row_has_crash_join_id(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert row is not None
        assert row["crash_join_id"] == "250111396"

    def test_found_row_has_source(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert row["source"] == "mshp_troop_e"

    def test_found_row_scrapes_county(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert row["county"] == "New Madrid"

    def test_found_row_scrapes_date(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert row["report_date"] == "2025-01-11"

    def test_found_row_scrapes_location(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert "US-61" in row["location"]

    def test_contact_found_when_driver_present(self):
        row = self.p.normalize(RESULT_HTML, "250111396")
        assert row["contact_found"] is True

    def test_contact_not_found_when_absent(self):
        row = self.p.normalize("<html><body><p>Crash details only.</p></body></html>", "X")
        assert row is not None
        assert row["contact_found"] is False


# ---------------------------------------------------------------------------
# fetch() — mocked HTTP
# ---------------------------------------------------------------------------

def _make_response(status: int, text: str):
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


class TestFetch:
    def test_fetch_empty_ids_returns_empty(self):
        p = MissouriProvider()
        assert p.fetch(limit=5) == []

    def test_fetch_with_not_found_skips_row(self):
        p = MissouriProvider(accident_ids=["250111396"])

        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            session.get.return_value = _make_response(200, "")
            session.post.return_value = _make_response(200, NOT_FOUND_HTML)

            rows = p.fetch()

        assert rows == []

    def test_fetch_with_result_returns_row(self):
        p = MissouriProvider(troop="E", accident_ids=["250111396"])

        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            session.get.return_value = _make_response(200, "")
            session.post.return_value = _make_response(200, RESULT_HTML)

            rows = p.fetch()

        assert len(rows) == 1
        assert rows[0]["crash_join_id"] == "250111396"
        assert rows[0]["source"] == "mshp_troop_e"

    def test_fetch_limit_slices_ids(self):
        p = MissouriProvider(accident_ids=["1", "2", "3", "4", "5"])

        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=session)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            session.get.return_value = _make_response(200, "")
            session.post.return_value = _make_response(200, NOT_FOUND_HTML)

            p.fetch(limit=2)
            assert session.post.call_count == 2
