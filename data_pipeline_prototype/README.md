# Data Pipeline Prototype

A modular, provider-based data ingestion pipeline for earthquake data from USGS.

## Project Structure

```
data_pipeline_prototype/
├── providers/          # Data source providers
│   ├── base.py         # Base provider interface
│   └── usgs_earthquakes.py  # USGS earthquake provider
├── pipeline/           # Data processing pipeline
│   ├── collector.py    # Data collection
│   ├── transformer.py  # Data transformation
│   └── storage.py      # Data storage (JSON/CSV)
├── models/             # Data models and schemas
│   └── schema.py       # Record schema definitions
├── utils/              # Utility functions
│   ├── logger.py       # Logging setup
│   └── dedup.py        # Deduplication logic
├── data/               # Output directory
├── main.py             # Pipeline entry point
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore rules
├── COMMITS.md          # Commit history
└── README.md           # This file
```

## Setup

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

Run the pipeline:
```bash
python main.py
```

Contact enrichment environment variables:

```bash
GOOGLE_CREDS=path/to/creds.json
SHEET_NAME=crash_contacts
```

City ingestion schedules are configured in:

- core/schedules.py

Current defaults:

- chicago: 0 * * * *
- nyc: */15 * * * *
- houston: 30 * * * *

Schedule API endpoints:

- GET /ingestion/schedules
- GET /ingestion/schedules/{city}

Jurisdiction profile endpoint:

- GET /jurisdictions

## Jurisdiction Landscape

| Jurisdiction | Agency / Place | System Type | Access Model | Modernization Level | Notes |
| ---------------- | -------------------- | ------------------------- | ------------------------------- | -------------------- | ---------------------------------------- |
| Chicago, IL | Chicago Police / DOT | Legacy + hybrid portal | Public lookup + internal joins | Legacy web forms | RD-based lookup, manual + semi-automated |
| New York, NY | NYPD / NYC Open Data | Open data portal + API | Open API + public dataset | Modernized | Strong API ecosystem |
| Los Angeles, CA | LAPD / CHP | Mixed systems | Public request + partial API | Semi-modern | Some datasets open, some restricted |
| Houston, TX | HPD | Vendor + public portal | Request-based + limited lookup | Legacy-heavy | Often manual retrieval |
| Miami-Dade, FL | FHP / county system | Vendor-hosted system | Public lookup portal | Legacy vendor system | Slow, form-based search |
| Dallas, TX | DPD | Custom + public dashboard | Open data + request portal | Moderately modern | Mix of structured datasets |
| Atlanta, GA | APD | State + city hybrid | Open data + manual requests | Mixed legacy | Some APIs available |
| Philadelphia, PA | PPD | Legacy + state system | Request + partial public access | Legacy-heavy | Manual-heavy workflows |
| Phoenix, AZ | PD / DOT | Modern + open data | API + download datasets | Modernized | Strong GIS integration |
| Detroit, MI | DPD | Legacy system | Request portal + manual lookup | Legacy-heavy | Limited automation support |

## Features

- **Provider-based Architecture**: Extensible design for multiple data sources
- **Data Normalization**: Standardize data from different providers
- **Deduplication**: Remove duplicate records
- **Multiple Output Formats**: JSON and CSV storage
- **Logging**: Comprehensive logging system

## Requirements

- Python 3.12+
- requests: HTTP library
- pandas: Data manipulation
