# Prototype Data Pipeline

A lightweight, modular prototype for the Chicago Crashes data pipeline with plugin-based providers, ETL processing, and extensible architecture.

## 📁 Structure

```
prototype/
├── src/
│   ├── providers/       # Data provider plugins (USGS, Chicago Crashes, etc.)
│   ├── pipeline/        # ETL pipeline (collect, transform, store)
│   ├── utils/           # Shared utilities (logging, deduplication, etc.)
│   └── __init__.py
├── data/                # Input/output data directory
├── requirements.txt     # Python dependencies
└── README.md
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Pipeline

```bash
python -m src.pipeline.main
```

### 3. Run Tests

```bash
pytest
```

## 🔌 Architecture

- **Providers**: Extensible data source plugins
- **Pipeline**: Async ETL with retry logic and error handling
- **Storage**: Pluggable storage backends (SQLite, PostgreSQL)
- **Utils**: Shared helpers for logging, deduplication, etc.

## 📊 Available Providers

- `chicago_crashes` - Chicago traffic crash data
- `detroit_provider` - Detroit crash records via ArcGIS feature service (target: https://data.detroitmi.gov/datasets/traffic-crashes-dashboard)
- `lapd_provider` - LAPD public lookup automation via BuyCrash form submission
- `legacy_portal_provider` - generic aiohttp + BeautifulSoup form automation for legacy portal lookups
- `nyc_provider` - NYC crash data via Socrata API (`aiohttp`)
- `usgs_earthquakes` - USGS earthquake data
- (Extend with custom providers)

Legacy portal quick-start example (Pennsylvania PSP):

```python
from src.providers.legacy_portal_provider import LegacyPortalProvider

provider = LegacyPortalProvider(
    {
        "search_url": "https://appsca.pwp.pa.gov/psp/crash-reports/",
        "agency": "Pennsylvania State Police",
        "tokens_per_second": 2,
        "accident_ids": ["PA 2018-123456"],
    }
)

rows = provider.fetch()
```

Detroit provider quick-start:

```python
from src.providers.detroit_provider import DetroitProvider

provider = DetroitProvider()
rows = provider.fetch(limit=100)
```

## 🧪 Testing

```bash
pytest -v
pytest --cov=src
```

Manual testing seeds and extraction model notes are tracked in:
- `MANUAL_TESTING.md`

Machine-readable jurisdiction/provider profiles are tracked in:
- `jurisdictions.yaml`

Example profile-based legacy provider setup:

```python
from src.providers.legacy_portal_provider import LegacyPortalProvider

provider = LegacyPortalProvider.from_profile("pennsylvania_state_psp")
rows = provider.fetch(limit=10)
```

Run a profile directly from CLI:

```bash
python -m src.providers.run_profile pennsylvania_state_psp --limit 10 --pretty
```

## 📝 Development

Add new providers in `src/providers/` following the base provider interface.

```python
from src.providers.base import BaseProvider

class CustomProvider(BaseProvider):
    async def fetch(self):
        # Implementation
        pass
```

## 🌐 WorkerProvider Rotation (Rate-Limit Mitigation)

`ChicagoCrashesProvider` now uses a `WorkerProvider` for API calls and can rotate
user-agents and proxies between requests.

## 📈 High-Volume Expansion Strategy

To support checking thousands of random accident IDs per hour across Midwest jurisdictions, the prototype includes:

- Distributed Workers: modular `Provider` architecture makes city-specific connectors easy to add.
- Distributed Sequential Workers: `SequentialWorkerProvider.scan_ranges_distributed(...)` lets you run multiple random ID ranges concurrently while preserving sequential checks inside each range.
- Token Bucket Throttling: `src/utils/limiter.py` smooths request spikes so your IP is less likely to be flagged as bot traffic, which is especially important for legacy systems like St. Louis and Detroit portals.
- Privacy-First Joins: sensitive contact data from the private Google Sheet is merged locally and never committed to GitHub.

Set these optional environment variables before running the pipeline:

```bash
export WORKER_USER_AGENTS="Mozilla/5.0 (...Chrome...),Mozilla/5.0 (...Safari...)"
export WORKER_PROXIES="http://proxy1:8080,http://proxy2:8080"
export WORKER_MAX_ATTEMPTS="4"
export WORKER_RATE_LIMIT_CAPACITY="10"
export WORKER_RATE_LIMIT_TOKENS_PER_SECOND="2"
```

Notes:
- `WORKER_USER_AGENTS`: comma-separated user-agent strings.
- `WORKER_PROXIES`: comma-separated proxy URLs used round-robin.
- `WORKER_MAX_ATTEMPTS`: retries for HTTP 429 responses.
- `WORKER_RATE_LIMIT_CAPACITY`: max burst size before throttling.
- `WORKER_RATE_LIMIT_TOKENS_PER_SECOND`: steady-state request rate.

## Contacts Data

Real contact numbers (phone numbers, names, addresses) are stored in private Google Sheets:

- Chicago Crashes with Contacts: https://docs.google.com/spreadsheets/d/1HeSWYoEPxpE9bxrfMF_YMqCYYEm1QYNnwmTN9ljkgGg/edit?usp=drivesdk
- Additional Crash Contacts Sheet: https://docs.google.com/spreadsheets/d/1IYBqja8wMxDZxDVCqNRgPqDm65yJJE6Vysd4ymFY6O8/edit?gid=0#gid=0

Do not upload the raw sheet to GitHub due to privacy requirements.

The prototype can merge public crash data with the local contacts file using the `crash_join_id` column as the join key.

Safe local merge workflow:
1. Download the private sheet as CSV and name it contacts.csv.
2. Put contacts.csv in prototype/data.
3. Confirm contacts has crash_join_id. Older files with crash_id or rd are still accepted.
4. Run from prototype: python -m src.pipeline.merger.
5. Read merged results in prototype/data/merged_output.csv.

Privacy guardrails:
- Keep real contact files local only.
- Never commit contacts.csv or files from prototype/data_private.
- Use only fake data in shared templates such as contacts_template.csv.
