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
- `usgs_earthquakes` - USGS earthquake data
- (Extend with custom providers)

## 🧪 Testing

```bash
pytest -v
pytest --cov=src
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
