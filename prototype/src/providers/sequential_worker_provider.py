import asyncio
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .base import BaseProvider
from src.utils.limiter import RateLimiter


class SequentialWorkerProvider(BaseProvider):
    """Sequentially scans report IDs and collects normalized valid records."""

    def __init__(
        self,
        base_url: str,
        rate_limit: float = 5,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.limiter = RateLimiter(rate_limit)
        self.start_id = start_id
        self.end_id = end_id

    def fetch(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """
        BaseProvider-compatible sync entrypoint.

        Uses configured start_id/end_id and runs the async scanner.
        """
        if self.start_id is None or self.end_id is None:
            raise ValueError("start_id and end_id must be set to use fetch()")

        records = asyncio.run(self.scan_range(self.start_id, self.end_id, limit=limit))
        return [record for record in records if isinstance(record, dict)]

    async def scan_range(
        self,
        start_id: int,
        end_id: int,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Checks IDs sequentially in [start_id, end_id)."""
        if end_id <= start_id:
            return []

        results: List[Dict[str, Any]] = []
        for current_id in range(start_id, end_id):
            await self.limiter.wait()
            data = await self.fetch_single_report(current_id)
            if not data:
                continue

            results.append(self.normalize(data))
            if limit and len(results) >= limit:
                break

        return results

    async def scan_ranges_distributed(
        self,
        ranges: Sequence[Tuple[int, int]],
        *,
        per_range_limit: Optional[int] = None,
        max_concurrent_workers: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run multiple sequential range scans concurrently.

        Args:
            ranges: Sequence of (start_id, end_id) ranges using [start_id, end_id).
            per_range_limit: Optional limit applied to each individual range scan.
            max_concurrent_workers: Optional cap on simultaneous range workers.

        Returns:
            Flattened list of normalized records from all ranges.
        """
        if not ranges:
            return []

        worker_limit = len(ranges) if max_concurrent_workers is None else max(1, max_concurrent_workers)
        semaphore = asyncio.Semaphore(worker_limit)

        async def _run_one(start_id: int, end_id: int) -> List[Dict[str, Any]]:
            async with semaphore:
                return await self.scan_range(start_id, end_id, limit=per_range_limit)

        tasks = [_run_one(start_id, end_id) for start_id, end_id in ranges]
        grouped_results = await asyncio.gather(*tasks)

        merged: List[Dict[str, Any]] = []
        for rows in grouped_results:
            merged.extend(rows)
        return merged

    async def fetch_single_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Implementation hook for city-specific legacy portal fetching logic."""
        raise NotImplementedError("Subclasses must implement fetch_single_report")

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single legacy payload into pipeline-friendly shape."""
        return data
