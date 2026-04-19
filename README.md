🚗 ChicagoCrashes Data Pipeline + AI Risk System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue.svg)](https://www.docker.com/)
[![Deploy](https://img.shields.io/badge/Deploy-Docker%20Ready-2496ED.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)](https://www.postgresql.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Lightweight-orange.svg)](https://www.sqlite.org/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-black.svg)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

 Live Demo

 API Docs: https://your-live-url/docs  
Health Check: https://your-live-url/health  
 Risk Engine: POST /risk/analyze/usgs  

Overview

A modular **data pipeline + AI-powered risk detection system** built with FastAPI, featuring plugin-based ingestion, ETL processing, and generative AI explanations for anomaly detection.

Architecture Flow

External API → Provider → ETL Pipeline → Risk Engine → GenAI Explanation → API Response
Deployment Flow


GitHub Repo
   ↓
GitHub Actions
   ↓
Docker Build
   ↓
Google Cloud Run
   ↓
Public API URL
 Automated Deployment Pipeline

1. GitHub detects push — Any commit to `main` or manual trigger initiates the workflow
2. GitHub Actions starts pipeline — Workflow runs on Ubuntu runners with GCP authentication
3. Docker image is built — FastAPI app is containerized from source in `data_pipeline_prototype/`
4. Image is deployed to Cloud Run — Service is updated with the new container
5. Old version is replaced — Traffic automatically routes to the new deployment
6. New API is live — Swagger docs available at the public Cloud Run URL

 Key Features

Plugin-based provider architecture (extensible ingestion system)
Async data ingestion with retry + exponential backoff
ETL pipeline (collect → transform → store)
SQLite + PostgreSQL support
 FastAPI REST service with Swagger documentation
 Fully containerized (Docker + Docker Compose)
 Pytest-based test suite
 CI/CD ready (GitHub Actions)


 Quick Start

```bash
docker compose up --build

Deployment

Option 1: Google Cloud Run (with GitHub Actions)**

Prerequisites:
- Google Cloud project with Cloud Run API enabled
- Service account with `roles/run.admin` and related permissions
- `GCP_SA_KEY` secret stored in GitHub Settings → Secrets and Variables → Actions

The GitHub Actions workflow (`.github/workflows/deploy.yml`) automatically:
1. Builds a Docker image
2. Pushes to Google Artifact Registry
3. Deploys to Cloud Run
4. Outputs the public URL

Push to `main` branch to trigger deployment.

Live API: `https://data-pipeline-api-xxxxx.run.app`

Option 2: Render (1-Click Deploy)**

The repository includes `render.yaml` for instant Render deployment.

1. Fork or connect this repository to Render
2. Click "Deploy" — Render automatically detects `render.yaml`
3. Service starts on Render's free tier

Features:
- Auto-deploys on git push to `main`
- Health checks enabled (`/health`)
- Environment ready (no secrets needed for basic setup)

Live API: `https://your-app.onrender.com`
- Swagger Docs: `https://your-app.onrender.com/docs`
- Risk Analysis: `https://your-app.onrender.com/risk/analyze/usgs`
- Health Check: `https://your-app.onrender.com/health`

API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/providers` | GET | List available data providers |
| `/run/{provider_name}` | POST | Execute pipeline with specific provider |
| `/risk/analyze/usgs` | POST | AI risk analysis for earthquake data |

---

## Implementation Tracker

| Item You Want | Where It Should Be | Current Status | How to Add / Find It |
|---|---|---|---|
| Revised Contacts / Privacy Note | Root README.md (new section) | Added | See this section and prototype docs |
| Provider-based Prototype | New folder: prototype/ | Added | [prototype](prototype) |
| Chicago Crashes Schema | prototype/schema/ (JSON + CSV files) | Added | [prototype/schema](prototype/schema) |
| Contacts Template | prototype/data/contacts_template.csv | Added | [prototype/data/contacts_template.csv](prototype/data/contacts_template.csv) |
| Python Pipeline Code | Inside prototype/src/ | Added | [prototype/src/providers](prototype/src/providers) and [prototype/src/pipeline](prototype/src/pipeline) |
| Google Sheet with Real Contacts | Do NOT upload to GitHub | Private only | Keep local and merge by `rd` key |

## Contacts Data

Real contact numbers (phone numbers, names, addresses) are available in the private Google Sheet:

- [Chicago Crashes with Contacts](https://docs.google.com/spreadsheets/d/1HeSWYoEPxpE9bxrfMF_YMqCYYEm1QYNnwmTN9ljkgGg/edit?usp=drivesdk)

Do not upload the raw sheet to GitHub due to privacy reasons.

The prototype can merge public crash data with the contacts file locally using the `rd` column as the key.
