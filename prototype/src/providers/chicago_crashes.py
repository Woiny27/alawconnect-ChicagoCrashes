import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .base import BaseProvider
from .worker_provider import WorkerProvider

logger = logging.getLogger(__name__)


class ChicagoCrashesProvider(BaseProvider):
    """Fetches public crash records from the Chicago Data Portal API.

    Falls back to a local CSV when csv_path is provided, which is useful
    for offline development and tests.
    """

    API_URL = "https://data.cityofchicago.org/resource/85ca-t3if.json"
    TIMEOUT = 30

    def __init__(
        self,
        csv_path: Optional[Path] = None,
        worker_provider: Optional[WorkerProvider] = None,
    ) -> None:
        self.csv_path = csv_path
        self.worker_provider = worker_provider or WorkerProvider.from_env()

    def fetch(self, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
        if self.csv_path is not None:
            return self._fetch_local(limit)
        return self._fetch_api(limit)

    def _fetch_api(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"$order": "crash_date DESC"}
        if limit:
            params["$limit"] = limit

        logger.info("Fetching %s records from Chicago Data Portal...", limit)
        response = self.worker_provider.get(
            self.API_URL,
            params=params,
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()

        rows: List[Dict[str, Any]] = response.json()
        for row in rows:
            row["crash_join_id"] = row.get("crash_record_id", "")
        logger.info("Fetched %s records from API.", len(rows))
        return rows

    def _fetch_local(self, limit: Optional[int]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        assert self.csv_path is not None
        with self.csv_path.open("r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                row["crash_join_id"] = row.get("crash_record_id", "")
                rows.append(row)
                if limit and index >= limit:
                    break
        logger.info("Loaded %s records from local CSV.", len(rows))
        return rows
