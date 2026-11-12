# 🛠️ Developer Setup & Deployment Guide

This guide provides a comprehensive, step-by-step walkthrough for configuring, building, running, and testing the **Multilingual News Intelligence Platform** from a fresh clone.

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Cloning & Directory Navigation](#2-cloning--directory-navigation)
3. [Environment Configuration](#3-environment-configuration)
4. [Infrastructure Deployment (Docker)](#4-infrastructure-deployment-docker)
5. [Python Environment Setup](#5-python-environment-setup)
6. [Corpus and evaluation commands](#6-corpus-and-evaluation-commands)
7. [Starting the FastAPI Backend](#7-starting-the-fastapi-backend)
8. [Starting the Next.js Frontend](#8-starting-the-nextjs-frontend)
9. [Running Evaluations & Automated Tests](#9-running-evaluations--automated-tests)
10. [Troubleshooting & Common Pitfalls](#10-troubleshooting--common-pitfalls)

---

## 1. Prerequisites

Before setting up the project, ensure your host development machine has the following tools installed:

| Tool | Minimum Version | Recommended | Notes |
|---|---|---|---|
| **Operating System** | Ubuntu 22.04 LTS, macOS 13+, or Windows WSL2 | Linux (x86_64 or arm64) | Native Linux environment recommended |
| **Docker & Docker Compose** | Docker 24.0+ & Compose v2.20+ | Latest Docker Desktop / Engine | Required for Weaviate and MongoDB containers |
| **Python** | Python `3.11` or `3.12` | Python `3.12.x` | Managed via `uv`, `mise`, or `pyenv` |
| **Node.js & npm** | Node.js `20.x` (LTS) | Node.js `20.14+` or `22.x` | Required for Next.js 16 frontend (package currently pins Next.js 16.4.6) |
| **CUDA (Optional)** | CUDA 12.1+ | NVIDIA GPU (4 GB+ VRAM) | Enables fast FP16 inference for `bge-m3` and reranker |

> [!NOTE]
> An NVIDIA GPU is **optional**; CPU execution is available. The model smoke checks below require the real configured backend and fail if a deterministic or lexical fallback is used, so a fallback must not be reported as verified inference.

---

## 2. Cloning & Directory Navigation

Clone the repository to your local development environment:

```bash
git clone https://github.com/vasu/News-Intelligence-Platform.git
cd News-Intelligence-Platform
```

Inspect the repository root to verify required directories and files:
```bash
ls -la
# You should see: api/, config/, core/, data/, docs/, eval/, frontend/, infra/, Makefile, requirements.txt
```

---

## 3. Environment Configuration

The verified local runtime and spider path need MongoDB and Weaviate connection settings. A Gemini key is not required for the verified infrastructure, model, or crawler checks; any Gemini configuration is optional legacy behavior and is outside the current project scope.

### 3.1 Backend Environment (`.env`)

Copy the sample environment file to `.env`:

```bash
cp .env.example .env
```

Open `.env` in your editor of choice:
```env
# ==============================================================================
# Multilingual News Intelligence Platform - Environment Configuration
# ==============================================================================

# MongoDB Connection (matches infra/docker-compose.yml)
MONGO_URI=mongodb://localhost:27017

# Weaviate Vector Store (matches infra/docker-compose.yml)
WEAVIATE_HOST=localhost
WEAVIATE_PORT=8080
WEAVIATE_GRPC_PORT=50051
```

The Gemini summary and credibility paths are legacy project behavior and are
outside the current project scope. No summary provider has been verified. A
deterministic fallback response is not evidence that a summary, chat, or
credibility result is real.

### 3.2 Frontend Environment (`frontend/.env.local`)

Verify or create `frontend/.env.local`:
```bash
cat << 'EOF' > frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

---

## 4. Infrastructure Deployment (Docker)

The platform relies on two containerized databases configured in `infra/docker-compose.yml`:
- **MongoDB 7.0**: Document store for full articles, cluster memberships, and metadata.
- **Weaviate 1.27.3**: Vector database providing native dense cosine vector search and BM25 lexical search over chunk passages.

### 4.1 Launch Containers

Start the services in detached mode:

```bash
make up
# Equivalent to: docker compose -f infra/docker-compose.yml up -d
```

### 4.2 Verify Container Health

Run `docker compose ps` to verify container status:

```bash
docker compose -f infra/docker-compose.yml ps
```

You should see both containers running healthy:
```
NAME                   IMAGE                             COMMAND                  SERVICE    STATUS
news-intel-mongodb     mongo:7                           "docker-entrypoint.s…"   mongodb    Up (healthy)   0.0.0.0:27017->27017/tcp
news-intel-weaviate    semitechnologies/weaviate:1.27.3  "/bin/weaviate --hos…"   weaviate   Up (healthy)   0.0.0.0:8080->8080/tcp, 0.0.0.0:50051->50051/tcp
```

Test Weaviate readiness probe via `curl`:
```bash
curl -i http://localhost:8080/v1/.well-known/ready
# Expected HTTP/1.1 200 OK
```

Run the project smoke check to test MongoDB read-after-write in a separate
`news_intel_verification` database and Weaviate readiness:

```bash
make infra-smoke
```

It inserts a uniquely named temporary MongoDB record and removes that record
after the check. It does not touch the project corpus. Start the services with
`make up` first; this check does not start or stop containers.

To stop the containers at any time, run:
```bash
make down
# Equivalent to: docker compose -f infra/docker-compose.yml down
```

---

## 5. Python Environment Setup

Create an isolated Python virtual environment using standard `venv` or `uv`:

### Option A: Standard `venv`
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Option B: High-Speed `uv` (Recommended)
```bash
# If uv is installed (curl -LsSf https://astral.sh/uv/install.sh | sh)
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Verify key package installations:
```bash
python -c "import fastapi, weaviate, pymongo, torch; print('Environment initialized successfully!')"
```

### 5.1 Verify real local model inference

With the project's Python environment active and the configured model weights
available locally or downloadable, run each model in its own process. This
keeps both large models from occupying GPU memory at once:

```bash
python scripts/verify_models.py embedder
python scripts/verify_models.py reranker
```

The command reports the selected model, actual backend, device, elapsed time,
and output shape or score count. A `PASS` requires real FlagEmbedding or
CrossEncoder execution; the wrapper's mock or lexical fallback fails the
check. To test CPU execution explicitly, append `--device cpu`. To require
CUDA, append `--device cuda`; it exits with an error when CUDA is unavailable.
On the development machine used for this report, both commands passed on an
RTX 3050 Ti with CUDA fp16: BGE-M3 returned two finite 1,024-dimensional
vectors and the cross-encoder returned two finite scores. This verifies model
execution and output validity, not retrieval relevance or ranking quality.

The cross-encoder requests fp16 weights as it loads on CUDA to fit the 4 GB
GPU. CPU execution does not request fp16. Keep the two smoke commands separate
processes to release one model before loading the other.

### 5.2 Run a bounded Scrapy source pilot

Start MongoDB first (`make up`), then run one adapter from the repository root.
This command uses the project virtual environment and stores raw and normalized
records in the `news_intel` database:

```bash
SCRAPY_SETTINGS_MODULE=scrapers.settings .venv/bin/python -m scrapy crawl abp_en -a max_articles=10 -s MONGO_DATABASE=news_intel -s LOG_LEVEL=WARNING
```

Use one of `abp_en`, `abp_hi`, `abp_bn`, `abp_mr`, `oneindia_en`,
`amarujala_hi`, `news18_bn`, or `loksatta_mr` in place of `abp_en`. The
`max_articles` limit applies to article/section request pairs; the same
canonical article found in multiple mapped sections may be merged into one
normalized article with multiple section provenance entries. Inspect run
counters in MongoDB's `crawl_runs` collection. The global category IDs,
publisher sections, and routes are maintained in
[`scrapers/sources.py`](../scrapers/sources.py).

The 12 November 2026 UTC bounded live pilot fetched 102 request pairs, accepted
94 article records, rejected 8, and recorded one robots-obeyed candidate error
for OneIndia's disallowed `/partner-content/` path. This is a smoke campaign,
not a representative corpus or a claim of complete category coverage; see the
[verification report](VERIFICATION_REPORT.md) for per-adapter counts and
limitations. Do not bypass a publisher's robots exclusions.

---

## 6. Corpus and evaluation commands

The legacy dataset ingestion/index/cluster commands are not the verified
Scrapy-based research pipeline. In particular, `make ingest` refuses to write
to the configured application database because its legacy input files are not
the curated news corpus. Do not point it at `news_intel`, and do not assume
that ignored Parquet/vector files or old Mongo records are valid inputs.

The legacy loader may only be run for isolated investigation with an
explicitly selected disposable database distinct from the application
database. Review its source and dataset terms first. Existing ignored local
datasets and generated evaluation result files are preserved in place; they
are not current corpus or evaluation evidence. Legacy generated evaluation
entrypoints are disabled. Follow [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md) for the
supported collection, snapshot, indexing and evaluation workflow as each
slice is completed. Do not run `make index`, `make cluster` or `make eval` as
if they produced validated research results.

---

## 7. Starting the FastAPI Backend

Launch the asynchronous FastAPI application using Uvicorn:

```bash
make api
# Equivalent to: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API startup, endpoint behavior, and the end-to-end UI were not included in
these runtime checks. The previous setup guide contained a dated startup log;
it is removed here because it does not establish the current runtime or
summary-provider status. A passing health response alone would not certify
search, topic, or summary behavior.

### Health Check Verification
In another terminal, test the `/api/health` endpoint:
```bash
curl -s http://localhost:8000/api/health | jq .
```
Expected response:
```json
{
  "status": "ok",
  "services": {
    "mongodb": true,
    "weaviate": true
  }
}
```

Interactive OpenAPI Swagger documentation is accessible in your browser at:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 8. Starting the Next.js Frontend

In a new terminal window, navigate to the `frontend/` directory, install packages, and launch the Next.js development server:

```bash
cd frontend
npm install
npm run dev
```

The installed Next.js 16.4.6 development server will start on port `3000`:
```
   ▲ Next.js 16.4.6
   - Local:        http://localhost:3000
   - Environments: .env.local

 ✓ Starting...
 ✓ Ready in 1200ms
```

Open **[http://localhost:3000](http://localhost:3000)** to start the frontend.
The existing Chat, Search, and Clusters routes are legacy interface paths; they
have not passed the revised project acceptance checks and should not be used
as a faculty demo claim. The presentation target is Search, Topics, and Corpus
as defined in the [overhaul plan](OVERHAUL_PLAN.md). In particular, the old
chat and credibility screens and their deterministic fallback responses are
not validated product features.

---

## 9. Running Evaluations & Automated Tests

### 9.1 Focused verified checks

The following focused suites were run for the bounded model and scraper
changes:

```bash
.venv/bin/python -m unittest tests.test_rerank tests.test_scrapers -v
MONGO_TEST_URI=mongodb://localhost:27017 \
  MONGO_TEST_DATABASE=news_intel_scraper_test_local \
  .venv/bin/python -m unittest tests.test_scraper_mongo -v
```

The Mongo lifecycle test drops and recreates the database named in
`MONGO_TEST_DATABASE`; use a fresh disposable name with the required
`news_intel_scraper_test_` prefix. The reported run used a dedicated database.
These checks cover focused regressions, not the full application or user
experience. The revised corpus pipeline still needs the broader, repeatable
acceptance gates in the plan.

### 9.2 Legacy evaluation entrypoints

The old evaluation entrypoints, including `make eval`, are intentionally
disabled because their generated outputs are not valid evidence for this
project. Do not run them or use the existing ignored result files in a report.
The revised BM25/dense/hybrid retrieval and topic evaluation has not yet been
run on a frozen, validated news corpus. The plan specifies minimal,
risk-targeted checks for each implementation slice; broad duplicate test runs
are not required.

---

## 10. Troubleshooting & Common Pitfalls

### Issue 1: `Weaviate connection refused on port 8080 or 50051`
- **Cause**: Weaviate container is not running or still initializing.
- **Fix**: Check `docker compose -f infra/docker-compose.yml logs weaviate`. Ensure port 8080 and 50051 are not occupied by other services (e.g. Apache or local proxies).

### Issue 2: `CUDA Out of Memory (OOM)` during indexing
- **Cause**: Batch size too high for GPU VRAM.
- **Fix**: The embedding script runs in FP16 by default. If your GPU has $\le 4\text{ GB}$ VRAM, reduce the batch size or export `CUDA_VISIBLE_DEVICES=""` to use CPU execution:
  ```bash
  python -m core.index --batch-size 16 --device cpu
  ```

### Issue 3: Next.js Frontend cannot communicate with API
- **Cause**: CORS restriction or mismatched `NEXT_PUBLIC_API_URL`.
- **Fix**: Confirm FastAPI is running on `http://localhost:8000`. Confirm `frontend/.env.local` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`.
