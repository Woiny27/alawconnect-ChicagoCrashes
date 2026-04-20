import csv
import tempfile
from pathlib import Path

import pytest

from src.providers.chicago_crashes import ChicagoCrashesProvider
from src.providers.worker_provider import WorkerProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {
        "crash_record_id": "abc123",
        "crash_date": "2026-04-18T01:45:00.000",
        "street_no": "7100",
        "street_direction": "S",
        "street_name": "WESTERN AVE",
    },
    {
        "crash_record_id": "def456",
        "crash_date": "2026-04-17T10:00:00.000",
        "street_no": "41",
        "street_direction": "W",
        "street_name": "WACKER DR",
    },
    {
        "crash_record_id": "ghi789",
        "crash_date": "2026-04-16T08:30:00.000",
        "street_no": "4830",
        "street_direction": "N",
        "street_name": "CENTRAL PARK AVE",
    },
]


def _write_temp_csv(rows: list[dict]) -> Path:
    """Write sample rows to a temp CSV and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    tmp.close()
    return Path(tmp.name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fetch_returns_all_rows():
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch()
    assert len(rows) == 3


def test_fetch_respects_limit():
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch(limit=2)
    assert len(rows) == 2


def test_fetch_adds_crash_join_id():
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch()
    for row in rows:
        assert "crash_join_id" in row


def test_crash_join_id_matches_crash_record_id():
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch()
    for row in rows:
        assert row["crash_join_id"] == row["crash_record_id"]


def test_fetch_preserves_crash_date():
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch()
    assert rows[0]["crash_date"] == "2026-04-18T01:45:00.000"


def test_fetch_raises_for_missing_file():
    provider = ChicagoCrashesProvider(csv_path=Path("/nonexistent/file.csv"))
    with pytest.raises(FileNotFoundError):
        provider.fetch()


def test_fetch_limit_zero_returns_all():
    """A limit of 0 (falsy) should not apply the limit."""
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch(limit=0)
    assert len(rows) == 3


def test_normalize_renames_crash_record_id_to_crash_join_id():
    """
    Ensures that fetch() maps crash_record_id to crash_join_id on every row.
    The Chicago source uses crash_record_id; crash_join_id is the internal key.
    """
    csv_path = _write_temp_csv(SAMPLE_ROWS)
    provider = ChicagoCrashesProvider(csv_path=csv_path)
    rows = provider.fetch()

    assert len(rows) == 3
    for row in rows:
        assert "crash_join_id" in row
        assert row["crash_join_id"] == row["crash_record_id"]
        # The source field is still present; crash_join_id is an added alias.
        assert row["crash_join_id"] != ""


def test_fetch_handles_missing_file_gracefully():
    """
    Validates that the provider raises FileNotFoundError when the source
    CSV is absent rather than silently returning an empty list.
    """
    provider = ChicagoCrashesProvider(csv_path=Path("/nonexistent/crashes.csv"))
    with pytest.raises(FileNotFoundError):
        provider.fetch(limit=1)


class _StubResponse:
    def __init__(self, status_code: int, payload: list[dict] | None = None):
        self.status_code = status_code
        self._payload = payload or []

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 429:
            raise RuntimeError(f"HTTP {self.status_code}")


class _StubSession:
    def __init__(self, responses: list[_StubResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


class _StubLimiter:
    def __init__(self):
        self.calls = 0

    def acquire(self, tokens=1.0):
        self.calls += 1


def test_worker_provider_rotates_user_agents_and_proxies():
    session = _StubSession([_StubResponse(200, [{"ok": True}]), _StubResponse(200, [{"ok": True}])])
    worker = WorkerProvider(
        user_agents=["ua-1", "ua-2"],
        proxies=["http://p1", "http://p2"],
        session=session,
        max_attempts=1,
    )

    worker.get("https://example.com")
    worker.get("https://example.com")

    assert session.calls[0]["headers"]["User-Agent"] == "ua-1"
    assert session.calls[1]["headers"]["User-Agent"] == "ua-2"
    assert session.calls[0]["proxies"]["http"] == "http://p1"
    assert session.calls[1]["proxies"]["http"] == "http://p2"


def test_worker_provider_retries_on_rate_limit_429():
    session = _StubSession([
        _StubResponse(429),
        _StubResponse(200, [{"crash_record_id": "1"}]),
    ])
    worker = WorkerProvider(
        user_agents=["ua-1", "ua-2"],
        session=session,
        max_attempts=2,
    )

    response = worker.get("https://example.com")

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert session.calls[0]["headers"]["User-Agent"] == "ua-1"
    assert session.calls[1]["headers"]["User-Agent"] == "ua-2"


def test_worker_provider_uses_token_bucket_limiter_on_each_attempt():
    session = _StubSession([_StubResponse(200, [{"ok": True}])])
    limiter = _StubLimiter()
    worker = WorkerProvider(session=session, max_attempts=1, limiter=limiter)

    worker.get("https://example.com")

    assert limiter.calls == 1


def test_chicago_crashes_provider_uses_worker_provider_for_api_calls():
    payload = [{"crash_record_id": "abc123"}]
    session = _StubSession([_StubResponse(200, payload)])
    worker = WorkerProvider(session=session, max_attempts=1)
    provider = ChicagoCrashesProvider(worker_provider=worker)

    rows = provider.fetch(limit=1)

    assert len(session.calls) == 1
    assert rows[0]["crash_join_id"] == "abc123"
