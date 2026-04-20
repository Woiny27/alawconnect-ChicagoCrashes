import requests
from typing import Any, Dict, List, Optional

from .base import BaseProvider

_CRASHES_URL = "https://data.cityofchicago.org/resource/85ca-t3if.json"
_DEFAULT_LIMIT = 1000


class ChicagoProvider(BaseProvider):
    """Fetches Chicago traffic crash records from the City of Chicago Open Data API."""

    def __init__(self, url: str = _CRASHES_URL) -> None:
        self.url = url

    def fetch(self, limit: Optional[int] = _DEFAULT_LIMIT) -> List[Dict[str, Any]]:
        """Fetch crash rows from the Socrata API.

        Args:
            limit: Maximum number of rows to return.  Pass ``None`` to use the
                   API's own default (typically 1000).

        Returns:
            A list of dicts, one per crash record.
        """
        params: Dict[str, object] = {}
        if limit is not None:
            params["$limit"] = limit

        response = requests.get(self.url, params=params, timeout=30)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise requests.HTTPError(
                f"Chicago crashes API request failed (url={self.url}, "
                f"status={response.status_code}): {exc}",
                response=response,
            ) from exc
        return response.json()


def build_rd_no_map(rows: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build a mapping from ``rd_no`` to ``crash_record_id`` (crash join ID).

    The Chicago crash dataset exposes ``rd_no`` as the police Records Division
    number while ``crash_record_id`` is the stable key used to join the Crashes
    dataset with the Vehicles and People datasets.

    Args:
        rows: Raw crash rows as returned by :meth:`ChicagoProvider.fetch`.

    Returns:
        A dict ``{rd_no: crash_record_id}`` for every row that contains both
        fields.  Rows missing either field are silently skipped.
    """
    mapping: Dict[str, str] = {}
    for row in rows:
        rd_no = row.get("rd_no")
        crash_record_id = row.get("crash_record_id")
        if rd_no and crash_record_id:
            mapping[rd_no] = crash_record_id
    return mapping
