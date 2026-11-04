# 🛠️ Developer Setup & Deployment Guide

This guide provides a comprehensive, step-by-step walkthrough for configuring, building, running, and testing the **Multilingual News Intelligence Platform** from a fresh clone.

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Cloning & Directory Navigation](#2-cloning--directory-navigation)
3. [Environment Configuration](#3-environment-configuration)
4. [Infrastructure Deployment (Docker)](#4-infrastructure-deployment-docker)
5. [Python Environment Setup](#5-python-environment-setup)
6. [Offline Data Pipeline (Ingest, Index, Cluster)](#6-offline-data-pipeline-ingest-index-cluster)
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
| **Node.js & npm** | Node.js `20.x` (LTS) | Node.js `20.14+` or `22.x` | Required for Next.js 16 frontend |
| **CUDA (Optional)** | CUDA 12.1+ | NVIDIA GPU (4 GB+ VRAM) | Enables fast FP16 inference for `bge-m3` and reranker |

> [!NOTE]
> An NVIDIA GPU is **optional**. The system automatically detects CUDA availability and gracefully falls back to CPU execution or lightweight representations when running on machines without a discrete GPU.

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

The application requires environment configuration for database ports, model flags, and the Google Gemini API key.

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

# Google Gemini API Key for English RAG synthesis with citations
# If left blank, the platform automatically utilizes deterministic offline fallback responses
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB Connection (matches infra/docker-compose.yml)
MONGO_URI=mongodb://localhost:27017

# Weaviate Vector Store (matches infra/docker-compose.yml)
WEAVIATE_HOST=localhost
WEAVIATE_PORT=8080
WEAVIATE_GRPC_PORT=50051
```

> [!TIP]
> You can acquire a free Google AI Studio API key at [ai.google.dev](https://ai.google.dev/). If no key is supplied, all RAG and credibility components will transparently use the built-in deterministic fallback generator, allowing full end-to-end testing without external API credentials.

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

---

## 6. Offline Data Pipeline (Ingest, Index, Cluster)

The offline data pipeline populates MongoDB and Weaviate with the processed multilingual news dataset.

```
┌──────────────┐     ┌─────────────┐     ┌────────────────┐
│ make ingest  │ ──> │ make index  │ ──> │  make cluster  │
└──────────────┘     └─────────────┘     └────────────────┘
 (MongoDB load)       (Embed & Vector)    (BERTopic UMAP)
```

### Step 6.1: Ingestion (`make ingest`)

```bash
make ingest
# Equivalent to: python -m core.ingest
```

**What this executes**:
1. Checks for raw dataset files under `data/raw/` or downloads standard splits from [L3Cube-IndicNews](https://github.com/l3cube-pune/indic-nlp) (English, Hindi, Bengali, Tamil) and HinFakeNews.
2. Performs exact deduplication using normalized `SHA-256` hashing.
3. Performs near-duplicate filtering within each language using token overlap shingles.
4. Normalizes article fields (`_id`, `lang`, `title`, `body`, `category`, `source`, `url`, `date`).
5. Inserts articles into the MongoDB `articles` collection and builds compound indices on `lang`, `category`, and `cluster_id`.

### Step 6.2: Chunking & Vector Indexing (`make index`)

```bash
make index
# Equivalent to: python -m core.index
```

**What this executes**:
1. Splits article bodies into overlapping windows of max 256 tokens (with 32 token overlap) using the `BAAI/bge-m3` tokenizer.
2. Prepends the article headline to every chunk to retain global contextual awareness.
3. Generates 1024-dimensional dense vectors using `BAAI/bge-m3` in FP16 precision.
4. Creates the `NewsChunk` collection in Weaviate with vector indexing and BM25 property mappings.
5. Batch uploads chunk texts, dense vectors, and metadata into Weaviate.
6. Serializes chunk mappings to `data/chunks_final.parquet` and vectors to `data/vectors.npy` for rapid offline reuse.

### Step 6.3: Cross-Lingual Topic Clustering (`make cluster`)

```bash
make cluster
# Equivalent to: python -m core.cluster
```

**What this executes**:
1. Loads document vectors from `data/vectors.npy` and article identifiers.
2. Runs **BERTopic** dimensionality reduction via **UMAP** (reducing 1024 dimensions down to 5).
3. Clusters vectors using **HDBSCAN** (minimum cluster size = 15).
4. Computes class-based TF-IDF (`c-TF-IDF`) to extract top descriptive keywords per cluster.
5. Computes multilingual distribution counts (`en`, `hi`, `bn`, `ta`) per cluster.
6. Writes cluster definitions to MongoDB `clusters` collection and tags each article with its corresponding `cluster_id`.

---

## 7. Starting the FastAPI Backend

Launch the asynchronous FastAPI application using Uvicorn:

```bash
make api
# Equivalent to: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Startup Log Output
You should observe logs indicating initialization of models and database connections:
```
INFO:     Started server process [28491]
INFO:     Waiting for application startup.
2026-11-04 12:30:00 [INFO] api.main: Initializing backend services and models...
2026-11-04 12:30:02 [INFO] api.main: EmbedModel initialized.
2026-11-04 12:30:03 [INFO] api.main: RerankModel initialized.
2026-11-04 12:30:03 [INFO] api.main: Connected to MongoDB at mongodb://localhost:27017 (db: news_intel)
2026-11-04 12:30:03 [INFO] api.main: Weaviate client initialized.
2026-11-04 12:30:03 [INFO] api.main: Gemini Flash client initialized.
2026-11-04 12:30:03 [INFO] api.main: Backend initialization complete.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

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

The Next.js 16 development server will start on port `3000`:
```
   ▲ Next.js 16.4.0
   - Local:        http://localhost:3000
   - Environments: .env.local

 ✓ Starting...
 ✓ Ready in 1200ms
```

Open your browser to **[http://localhost:3000](http://localhost:3000)**. You can now explore:
- **Chat (`/chat`)**: Ask questions in English, Hindi, Bengali, or Tamil; observe synthesized English responses with citations, credibility meters, and veracity explanations.
- **Search (`/search`)**: Run Hybrid, Dense, or BM25 queries across multilingual articles with language filtering pills.
- **Clusters (`/clusters`)**: Inspect cross-lingual topic clusters, view multilingual language ratios, and browse member articles.

---

## 9. Running Evaluations & Automated Tests

### 9.1 Unit & Integration Tests

Run the test suite with `pytest`:

```bash
pytest tests/ -v
```

This verifies:
- Citation regex extraction and citation-passage mapping (`tests/test_rag.py`).
- Weaviate search filtering, deduplication, and score normalizers (`tests/test_retrieval.py`).

### 9.2 Complete Benchmark Suite (`make eval`)

To reproduce the experimental results reported in the project documentation:

```bash
make eval
# Equivalent to: python -m eval.run_all
```

This automatically runs the 5 benchmark suites sequentially:
1. `eval/retrieval_flores.py`: FLORES-200 sentence retrieval comparison (BGE-M3 vs. multilingual-e5-base vs. BM25).
2. `eval/retrieval_news.py`: News retrieval ablation benchmark (BM25 $\rightarrow$ Dense $\rightarrow$ Hybrid $\rightarrow$ Cross-Encoder Reranker).
3. `eval/rag_eval.py`: RAG Faithfulness, Correctness, and Citation Accuracy vs. No-Retrieval generation.
4. `eval/cluster_eval.py`: Topic clustering NMI, ARI, and Multilingual Purity.
5. `eval/misinfo_eval.py`: Veracity classification Macro-F1 across English and Hindi test sets.

Results are printed in formatted terminal tables and saved to `results/*.json`.

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

### Issue 3: `GEMINI_API_KEY is not configured` warning
- **Cause**: Missing or unconfigured Gemini API key in `.env`.
- **Behavior**: The application does **not** crash. It automatically engages high-fidelity deterministic responses for chat and veracity verification so you can develop and demonstrate the application offline.
- **Fix**: Add a valid key from [Google AI Studio](https://aistudio.google.com/) to `.env` and restart the backend.

### Issue 4: Next.js Frontend cannot communicate with API
- **Cause**: CORS restriction or mismatched `NEXT_PUBLIC_API_URL`.
- **Fix**: Confirm FastAPI is running on `http://localhost:8000`. Confirm `frontend/.env.local` contains `NEXT_PUBLIC_API_URL=http://localhost:8000`.
