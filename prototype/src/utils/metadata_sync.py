"""metadata_sync.py — pull target crash IDs from a public Google Sheet.

The sheet is exported as CSV via the standard Google Sheets export endpoint.
No API key or OAuth is required as long as the sheet is set to "Anyone with
the link can view".

Usage::

    from src.utils.metadata_sync import fetch_target_ids

    ids = fetch_target_ids()          # uses the default sheet
    ids = fetch_target_ids(id_column="rd")  # if the key column is "rd"
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Public Google Sheet added in the project README.
# Sheet: https://docs.google.com/spreadsheets/d/1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8
_DEFAULT_SHEET_ID = "1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8"
_DEFAULT_GID = "0"
_EXPORT_URL_TEMPLATE = (
    "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
)

# Candidate column names that may hold the target crash/RD identifier.
_ID_COLUMN_CANDIDATES = ["crash_record_id", "crash_join_id", "rd", "id"]


def _build_export_url(sheet_id: str, gid: str) -> str:
    return _EXPORT_URL_TEMPLATE.format(sheet_id=sheet_id, gid=gid)


def fetch_sheet_df(
    sheet_id: str = _DEFAULT_SHEET_ID,
    gid: str = _DEFAULT_GID,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """Download the Google Sheet as a :class:`pandas.DataFrame`.

    Parameters
    ----------
    sheet_id:
        The unique identifier from the Google Sheets URL (the long alphanumeric
        string between ``/d/`` and ``/edit``).
    gid:
        The sheet tab identifier (``gid`` query parameter in the sheet URL).
    timeout:
        HTTP request timeout in seconds.
    session:
        Optional :class:`requests.Session` to use; a plain ``requests`` call is
        made when ``None``.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing every row from the sheet.

    Raises
    ------
    requests.HTTPError
        If the server responds with a non-2xx status code.
    ValueError
        If the downloaded content cannot be parsed as a CSV.
    """
    url = _build_export_url(sheet_id, gid)
    logger.info("Fetching Google Sheet CSV from %s", url)

    get = session.get if session is not None else requests.get
    response = get(url, timeout=timeout)
    response.raise_for_status()

    try:
        df = pd.read_csv(io.StringIO(response.text))
    except Exception as exc:
        raise ValueError(f"Failed to parse sheet content as CSV: {exc}") from exc

    logger.info("Sheet loaded: %d rows, columns: %s", len(df), list(df.columns))
    return df


def fetch_target_ids(
    sheet_id: str = _DEFAULT_SHEET_ID,
    gid: str = _DEFAULT_GID,
    id_column: Optional[str] = None,
    timeout: int = 30,
    session: Optional[requests.Session] = None,
) -> List[str]:
    """Return a deduplicated list of target crash IDs from the Google Sheet.

    The function tries to locate the ID column automatically by checking
    ``_ID_COLUMN_CANDIDATES`` in order, unless *id_column* is explicitly
    provided.

    Parameters
    ----------
    sheet_id:
        Google Sheets document ID.
    gid:
        Sheet tab GID.
    id_column:
        Exact column name to use as the identifier.  When ``None`` the first
        matching candidate from :data:`_ID_COLUMN_CANDIDATES` is used.
    timeout:
        HTTP request timeout in seconds.
    session:
        Optional :class:`requests.Session` for dependency injection / testing.

    Returns
    -------
    List[str]
        Deduplicated, non-empty target IDs in sheet order.

    Raises
    ------
    KeyError
        If the requested (or auto-detected) ID column is not found.
    """
    df = fetch_sheet_df(sheet_id=sheet_id, gid=gid, timeout=timeout, session=session)

    col = _resolve_id_column(df, id_column)
    logger.info("Using column %r as the target ID column", col)

    ids = (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s != ""]
        .drop_duplicates()
        .tolist()
    )

    logger.info("Found %d unique target IDs", len(ids))
    return ids


def _resolve_id_column(df: pd.DataFrame, id_column: Optional[str]) -> str:
    """Return the column name to use, raising :class:`KeyError` if absent."""
    if id_column is not None:
        if id_column not in df.columns:
            raise KeyError(
                f"Requested id_column {id_column!r} not found. "
                f"Available columns: {list(df.columns)}"
            )
        return id_column

    for candidate in _ID_COLUMN_CANDIDATES:
        if candidate in df.columns:
            return candidate

    # Fall back to the first column if none of the known candidates match.
    if df.columns.empty:
        raise KeyError("Sheet has no columns — cannot determine ID column.")

    first = df.columns[0]
    logger.warning(
        "None of %s found in sheet columns %s; falling back to first column %r",
        _ID_COLUMN_CANDIDATES,
        list(df.columns),
        first,
    )
    return first
