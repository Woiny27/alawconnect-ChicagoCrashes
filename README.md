# 🚗 ChicagoCrashes Data Pipeline + AI Risk System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Containerized-blue.svg)](https://www.docker.com/)
[![Deploy](https://img.shields.io/badge/Deploy-Docker%20Ready-2496ED.svg)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue.svg)](https://www.postgresql.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Lightweight-orange.svg)](https://www.sqlite.org/)
[![CI](https://img.shields.io/badge/CI-GitHub_Actions-black.svg)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🌍 Live Demo

👉 https://your-service.run.app/docs

---

## 🧠 Overview

A modular **data pipeline + AI-powered risk detection system** built with FastAPI, featuring plugin-based ingestion, ETL processing, and generative AI explanations for anomaly detection.

---

## 🧭 Architecture Flow

External Data -> Provider -> ETL Pipeline -> Risk Engine -> GenAI Explanation -> API Response -> Storage

---

## 🚀 Deployment Flow

```
GitHub Repo
   ↓
GitHub Actions
   ↓
Docker Build
   ↓
Google Cloud Run
   ↓
Public API URL
```

---

## 🔄 Automated Deployment Pipeline

1. **GitHub detects push** — Any commit to `main` or manual trigger initiates the workflow
2. **GitHub Actions starts pipeline** — Workflow runs on Ubuntu runners with GCP authentication
3. **Docker image is built** — FastAPI app is containerized from source in `data_pipeline_prototype/`
4. **Image is deployed to Cloud Run** — Service is updated with the new container
5. **Old version is replaced** — Traffic automatically routes to the new deployment
6. **New API is live** — Swagger docs available at the public Cloud Run URL

---

## ⚙️ Key Features

- 🔌 Plugin-based provider architecture (extensible ingestion system)
- ⚡ Async data ingestion with retry + exponential backoff
- 🔄 ETL pipeline (collect → transform → store)
- 🗄 SQLite + PostgreSQL support
- 🌐 FastAPI REST service with Swagger documentation
- 🐳 Fully containerized (Docker + Docker Compose)
- 🧪 Pytest-based test suite
- 🔁 CI/CD ready (GitHub Actions)

---

## 🚀 Quick Start

```bash
docker compose up --build
```