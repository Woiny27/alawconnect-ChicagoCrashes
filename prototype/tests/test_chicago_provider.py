"""Tests for ChicagoProvider and the rd_no → crash_record_id mapping."""

from unittest.mock import MagicMock, patch

import pytest

from src.providers.chicago import ChicagoProvider, build_rd_no_map

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {
        "rd_no": "JF100001",
        "crash_record_id": "abc0001",
        "crash_date": "2024-06-01T08:30:00.000",
        "crash_type": "NO INJURY / DRIVE AWAY",
        "most_severe_injury": "NO INDICATION OF INJURY",
        "latitude": "41.8781",
        "longitude": "-87.6298",
        "injuries_total": "0",
    },
    {
        "rd_no": "JF100002",
        "crash_record_id": "abc0002",
        "crash_date": "2024-06-02T14:15:00.000",
        "crash_type": "INJURY AND / OR TOW DUE TO CRASH",
        "most_severe_injury": "NONINCAPACITATING INJURY",
        "latitude": "41.8827",
        "longitude": "-87.6233",
        "injuries_total": "1",
    },
    {
        # Row missing rd_no — should be skipped by build_rd_no_map
        "crash_record_id": "abc0003",
        "crash_date": "2024-06-03T09:00:00.000",
        "crash_type": "NO INJURY / DRIVE AWAY",
        "most_severe_injury": "NO INDICATION OF INJURY",
        "latitude": "41.8700",
        "longitude": "-87.6500",
        "injuries_total": "0",
    },
    {
        # Row missing crash_record_id — should be skipped by build_rd_no_map
        "rd_no": "JF100004",
        "crash_date": "2024-06-04T11:00:00.000",
        "crash_type": "NO INJURY / DRIVE AWAY",
        "most_severe_injury": "NO INDICATION OF INJURY",
        "latitude": "41.8600",
        "longitude": "-87.6400",
        "injuries_total": "0",
    },
]


def _make_response(rows, status_code=200):
    """Return a mock requests.Response for the given rows."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = rows
    mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# ChicagoProvider.fetch
# ---------------------------------------------------------------------------


class TestChicagoProviderFetch:
    def test_returns_list_of_dicts(self):
        mock_resp = _make_response(SAMPLE_ROWS[:2])
        with patch("src.providers.chicago.requests.get", return_value=mock_resp):
            provider = ChicagoProvider()
            result = provider.fetch(limit=2)

        assert isinstance(result, list)
        assert all(isinstance(row, dict) for row in result)

    def test_passes_limit_param_to_api(self):
        mock_resp = _make_response([])
        with patch("src.providers.chicago.requests.get", return_value=mock_resp) as mock_get:
            provider = ChicagoProvider()
            provider.fetch(limit=50)

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["$limit"] == 50

    def test_no_limit_param_when_none(self):
        mock_resp = _make_response([])
        with patch("src.providers.chicago.requests.get", return_value=mock_resp) as mock_get:
            provider = ChicagoProvider()
            provider.fetch(limit=None)

        _, kwargs = mock_get.call_args
        assert "$limit" not in kwargs["params"]

    def test_row_contains_expected_fields(self):
        mock_resp = _make_response(SAMPLE_ROWS[:1])
        with patch("src.providers.chicago.requests.get", return_value=mock_resp):
            provider = ChicagoProvider()
            rows = provider.fetch()

        row = rows[0]
        assert row["rd_no"] == "JF100001"
        assert row["crash_record_id"] == "abc0001"
        assert row["crash_type"] == "NO INJURY / DRIVE AWAY"
        assert row["most_severe_injury"] == "NO INDICATION OF INJURY"

    def test_latitude_longitude_preserved_as_strings(self):
        """The Socrata API returns lat/lon as strings; verify they are not coerced."""
        mock_resp = _make_response(SAMPLE_ROWS[:1])
        with patch("src.providers.chicago.requests.get", return_value=mock_resp):
            provider = ChicagoProvider()
            rows = provider.fetch()

        assert rows[0]["latitude"] == "41.8781"
        assert rows[0]["longitude"] == "-87.6298"

    def test_http_error_raises_with_context(self):
        import requests as _requests

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = _requests.HTTPError(
            "Server Error", response=mock_resp
        )

        with patch("src.providers.chicago.requests.get", return_value=mock_resp):
            provider = ChicagoProvider()
            with pytest.raises(_requests.HTTPError, match="Chicago crashes API request failed"):
                provider.fetch()

    def test_custom_url_is_used(self):
        mock_resp = _make_response([])
        custom_url = "https://example.com/custom.json"
        with patch("src.providers.chicago.requests.get", return_value=mock_resp) as mock_get:
            provider = ChicagoProvider(url=custom_url)
            provider.fetch()

        args, _ = mock_get.call_args
        assert args[0] == custom_url


# ---------------------------------------------------------------------------
# build_rd_no_map
# ---------------------------------------------------------------------------


class TestBuildRdNoMap:
    def test_maps_rd_no_to_crash_record_id(self):
        mapping = build_rd_no_map(SAMPLE_ROWS)
        assert mapping["JF100001"] == "abc0001"
        assert mapping["JF100002"] == "abc0002"

    def test_skips_rows_missing_rd_no(self):
        mapping = build_rd_no_map(SAMPLE_ROWS)
        # SAMPLE_ROWS[2] has no rd_no; its crash_record_id should NOT appear as a value
        # keyed by an empty string
        assert "" not in mapping

    def test_skips_rows_missing_crash_record_id(self):
        mapping = build_rd_no_map(SAMPLE_ROWS)
        # SAMPLE_ROWS[3] has rd_no but no crash_record_id — must not appear
        assert "JF100004" not in mapping

    def test_empty_input_returns_empty_dict(self):
        assert build_rd_no_map([]) == {}

    def test_all_valid_rows_are_included(self):
        rows = [
            {"rd_no": f"RD{i:04d}", "crash_record_id": f"CID{i:04d}"}
            for i in range(10)
        ]
        mapping = build_rd_no_map(rows)
        assert len(mapping) == 10

    def test_duplicate_rd_no_last_write_wins(self):
        rows = [
            {"rd_no": "JF999", "crash_record_id": "FIRST"},
            {"rd_no": "JF999", "crash_record_id": "SECOND"},
        ]
        mapping = build_rd_no_map(rows)
        assert mapping["JF999"] == "SECOND"

    def test_returns_only_string_values(self):
        rows = [{"rd_no": "X1", "crash_record_id": "Y1", "extra": 99}]
        mapping = build_rd_no_map(rows)
        assert isinstance(mapping["X1"], str)
