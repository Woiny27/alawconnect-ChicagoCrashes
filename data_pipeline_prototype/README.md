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
