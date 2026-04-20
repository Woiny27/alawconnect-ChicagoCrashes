## 🏗️ Architecture

![System Architecture](assets/architecture.png)

This document describes the current architecture of the data pipeline prototype and how ingestion, scheduling, and risk analysis fit together.

## Scope

Primary implementation lives under `data_pipeline_prototype/` and is exposed through a FastAPI service.

## High-Level Components

- API layer: `data_pipeline_prototype/api/`
- Provider registry and plugins: `data_pipeline_prototype/core/registry.py`, `data_pipeline_prototype/plugins/`
- Pipeline orchestration: `data_pipeline_prototype/core/pipeline.py`
- HTTP client and retry policy: `data_pipeline_prototype/core/async_client.py`, `data_pipeline_prototype/core/retry.py`
- Storage backends: `data_pipeline_prototype/storage/`
- Risk scoring and explanation: `risk/`
- Scheduling and jurisdiction intelligence: `data_pipeline_prototype/core/schedules.py`

## Runtime Flow

1. API startup initializes `PluginRegistry` and loads provider plugins.
2. A run request selects a provider by name.
3. `Pipeline.run()` fetches provider data, normalizes records, deduplicates by ID, and writes to storage.
4. Risk endpoints score records and produce human-readable explanations.

## Data Flow

- Inbound source data enters through provider `fetch()` methods.
- Pipeline transforms source payload into normalized records.
- Deduplication removes duplicates by record ID.
- Persisted records are written by storage backend (`SQLiteStorage` in current API route).

## Scheduling Model

Scheduling configuration is centralized in `data_pipeline_prototype/core/schedules.py`.

Current ingestion cron map:

- chicago: `0 * * * *`
- nyc: `*/15 * * * *`
- houston: `30 * * * *`

The API exposes schedule metadata:

- `GET /ingestion/schedules`
- `GET /ingestion/schedules/{city}`

Note: this repository currently stores schedule configuration and exposes it through the API; execution of cron-triggered jobs is expected to be handled by an external scheduler or future worker process.

## Jurisdiction Intelligence

Jurisdiction operational profiles are maintained in `data_pipeline_prototype/core/schedules.py` and exposed via:

- `GET /jurisdictions`

This supports planning of ingestion strategy (for example: API-first vs portal/manual workflows) based on modernization/access characteristics.

## API Surface (Core)

- `GET /health`: service liveness check
- `GET /providers`: loaded providers
- `POST /run/{provider_name}`: execute provider pipeline
- `GET /ingestion/schedules`: list city cron schedules
- `GET /ingestion/schedules/{city}`: get one city cron schedule
- `GET /jurisdictions`: list jurisdiction system/access profiles
- `POST /risk/analyze/usgs`: score and explain USGS earthquake risk

## Extension Points

### Add a provider

1. Implement provider fetch logic.
2. Register provider through a plugin module and `register(registry)` hook.
3. Ensure output can be normalized by the pipeline.

### Add a new city schedule

1. Add city key and cron expression to `INGESTION_JOBS` in `data_pipeline_prototype/core/schedules.py`.
2. If needed, map city to provider in runner/worker logic.

### Add worker execution

To move from configuration-only scheduling to automated execution:

1. Add a scheduler process (for example APScheduler or platform cron).
2. Read `INGESTION_JOBS` as source of truth.
3. Trigger `POST /run/{provider_name}` or invoke pipeline directly.

## Reliability Considerations

- Provider requests should use retry/backoff logic where possible.
- Vendor-hosted or legacy portals may require anti-rate-limit tactics (proxy/user-agent rotation) at provider/worker level.
- Keep storage writes idempotent where feasible.
- Keep provider failures isolated from API process stability.

## Deployment Notes

Render deployment configuration is at `render.yaml`.
Current service model is a web process; scheduled execution needs an external scheduler or an additional worker service definition.
