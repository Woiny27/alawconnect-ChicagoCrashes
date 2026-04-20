import asyncio
from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseProvider


class NYCProvider(BaseProvider):
    """Fetch NYC crash records from the Socrata API using aiohttp."""

    API_URL = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"

    def __init__(self, app_token: Optional[str] = None, timeout_seconds: int = 30) -> None:
        self.app_token = app_token
        self.timeout_seconds = timeout_seconds

    def fetch(self, limit: Optional[int] = 100) -> List[Dict[str, str]]:
        """BaseProvider-compatible sync entrypoint."""
        records = asyncio.run(self.fetch_async(limit=limit))
        return [record for record in records if isinstance(record, dict)]

    async def fetch_async(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        """Fetch records asynchronously from the NYC Socrata endpoint."""
        params: Dict[str, Any] = {"$order": "crash_date DESC"}
        if limit:
            params["$limit"] = limit

        headers: Dict[str, str] = {}
        if self.app_token:
            headers["X-App-Token"] = self.app_token

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(self.API_URL, params=params, headers=headers) as response:
                response.raise_for_status()
                rows = await response.json()

        return [self.normalize(row) for row in rows if isinstance(row, dict)]

    @staticmethod
    def normalize(row: Dict[str, Any]) -> Dict[str, Any]:
        """Attach crash_join_id to align with internal merge conventions."""
        output = dict(row)
        output["crash_join_id"] = str(row.get("collision_id", "")).strip()
        return output
