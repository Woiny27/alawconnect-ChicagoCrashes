import asyncio

from src.providers.sequential_worker_provider import SequentialWorkerProvider


class _StubSequentialProvider(SequentialWorkerProvider):
    def __init__(self, existing_ids: set[int], **kwargs):
        super().__init__(base_url="https://legacy.example", **kwargs)
        self.existing_ids = existing_ids
        self.calls: list[int] = []
        self.inflight = 0
        self.max_seen_inflight = 0

    async def fetch_single_report(self, report_id: int):
        self.inflight += 1
        self.max_seen_inflight = max(self.max_seen_inflight, self.inflight)
        await asyncio.sleep(0)
        self.calls.append(report_id)
        self.inflight -= 1
        if report_id in self.existing_ids:
            return {
                "report_id": str(report_id),
                "crash_join_id": str(report_id),
            }
        return None


def test_scan_range_checks_ids_sequentially_and_collects_valid_rows():
    provider = _StubSequentialProvider(existing_ids={100, 102}, rate_limit=1000)

    rows = asyncio.run(provider.scan_range(100, 103))

    assert provider.calls == [100, 101, 102]
    assert [row["report_id"] for row in rows] == ["100", "102"]


def test_scan_range_respects_limit():
    provider = _StubSequentialProvider(existing_ids={200, 201, 202}, rate_limit=1000)

    rows = asyncio.run(provider.scan_range(200, 205, limit=2))

    assert [row["report_id"] for row in rows] == ["200", "201"]
    assert provider.calls == [200, 201]


def test_fetch_uses_configured_range():
    provider = _StubSequentialProvider(
        existing_ids={300, 302},
        rate_limit=1000,
        start_id=300,
        end_id=303,
    )

    rows = provider.fetch()

    assert [row["report_id"] for row in rows] == ["300", "302"]


def test_fetch_requires_range_configuration():
    provider = _StubSequentialProvider(existing_ids={1}, rate_limit=1000)

    try:
        provider.fetch()
        raised = False
    except ValueError:
        raised = True

    assert raised is True


def test_scan_ranges_distributed_collects_from_multiple_ranges():
    provider = _StubSequentialProvider(existing_ids={10, 12, 20, 21}, rate_limit=1000)

    rows = asyncio.run(
        provider.scan_ranges_distributed(
            [(10, 13), (20, 22)],
            max_concurrent_workers=2,
        )
    )

    assert sorted(row["report_id"] for row in rows) == ["10", "12", "20", "21"]


def test_scan_ranges_distributed_respects_worker_cap():
    provider = _StubSequentialProvider(existing_ids={1, 2, 3, 4}, rate_limit=1000)

    asyncio.run(
        provider.scan_ranges_distributed(
            [(1, 3), (3, 5)],
            max_concurrent_workers=1,
        )
    )

    assert provider.max_seen_inflight == 1
