import asyncio
from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseProvider


class DetroitProvider(BaseProvider):
    """Fetch Detroit crash records from the ArcGIS Traffic_Crashes feature layer."""

    TARGET_URL = "https://data.detroitmi.gov/datasets/traffic-crashes-dashboard"
    FEATURE_SERVICE_URL = "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/Traffic_Crashes/FeatureServer"

    def __init__(self, layer_id: int = 0, timeout_seconds: int = 30) -> None:
        self.layer_id = layer_id
        self.timeout_seconds = timeout_seconds

    def fetch(self, limit: Optional[int] = 100) -> List[Dict[str, str]]:
        """BaseProvider-compatible sync entrypoint."""
        records = asyncio.run(self.fetch_async(limit=limit))
        return [record for record in records if isinstance(record, dict)]

    async def fetch_async(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """Fetch records from ArcGIS REST query endpoint."""
        endpoint = f"{self.FEATURE_SERVICE_URL}/{self.layer_id}/query"
        params: Dict[str, Any] = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }
        if limit:
            params["resultRecordCount"] = int(limit)

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(endpoint, params=params) as response:
                response.raise_for_status()
                payload = await response.json()

        features = payload.get("features", [])
        rows = [feature.get("attributes", {}) for feature in features if isinstance(feature, dict)]
        return [self.normalize(row) for row in rows if isinstance(row, dict)]

    @staticmethod
    def normalize(row: Dict[str, Any]) -> Dict[str, Any]:
        """Attach crash_join_id and source metadata for pipeline alignment."""
        output = dict(row)
        crash_id = row.get("crash_id")
        if crash_id is None:
            crash_id = row.get("OBJECTID")

        output["crash_join_id"] = str(crash_id).strip() if crash_id is not None else ""
        output["source"] = "detroit_traffic_crashes"
        return output
