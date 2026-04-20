from unittest.mock import MagicMock, patch

from src.utils.metadata_sync import (
    google_sheet_url_to_csv_export_url,
    read_metadata_rows,
)


def test_google_sheet_url_to_csv_export_url_uses_query_gid():
    url = (
        "https://docs.google.com/spreadsheets/d/"
        "1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8/edit?gid=42#gid=0"
    )
    out = google_sheet_url_to_csv_export_url(url)
    assert out.endswith("/export?format=csv&gid=42")


def test_google_sheet_url_to_csv_export_url_uses_fragment_gid_when_query_missing():
    url = (
        "https://docs.google.com/spreadsheets/d/"
        "1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8/edit#gid=7"
    )
    out = google_sheet_url_to_csv_export_url(url)
    assert out.endswith("/export?format=csv&gid=7")


def test_read_metadata_rows_from_google_sheet_url_downloads_csv_text():
    sheet_url = (
        "https://docs.google.com/spreadsheets/d/"
        "1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8/edit?gid=0#gid=0"
    )
    csv_text = "crash_join_id,target_id\nC-1001,TGT-1\n"

    mock_response = MagicMock()
    mock_response.text = csv_text
    mock_response.raise_for_status = MagicMock()

    with patch("src.utils.metadata_sync.requests.get", return_value=mock_response) as mock_get:
        rows = read_metadata_rows(sheet_url)

    assert rows == [{"crash_join_id": "C-1001", "target_id": "TGT-1"}]
    called_url = mock_get.call_args.args[0]
    assert "/export?format=csv&gid=0" in called_url
