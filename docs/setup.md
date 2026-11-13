# 🛠️ Developer Setup & Deployment Guide

This guide covers the checked local setup commands and the current faculty demo path. A fresh CPU dependency-lock install/import gate passed separately; a fresh clone, CPU model inference, and complete fresh-clone collection-to-demo pipeline have not been rehearsed.

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
| **Python** | Python `3.12` | Python `3.12.15` | CPU lock verification used mise Python 3.12.15 and uv 0.8.23 (observed, not pinned) |
| **Node.js & npm** | Node.js `20.x` (LTS) | Node.js `20.14+` or `22.x` | Required for Next.js 16 frontend (package currently pins Next.js 16.4.6) |
| **CUDA (Optional)** | CUDA 12.1+ | NVIDIA GPU (4 GB+ VRAM) | Enables fast FP16 inference for `bge-m3` and reranker |

> [!NOTE]
> CUDA is optional. The lock resolves CPU Torch (`2.15.0+cpu`); fresh CPU dependency and import checks passed, but CPU model inference was not verified. The existing working CUDA environment was preserved. Do not sync the CPU lock into it.

---

## 2. Cloning & Directory Navigation

To create a working checkout (this command alone does not reproduce ignored local data or model weights):

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

Run the project smoke check to test MongoDB read-after-write in the isolated
`news_intel_verification` database and a temporary Weaviate vector
write/read/delete round trip:

```bash
make infra-smoke
```

It inserts and removes a uniquely named MongoDB record and creates, verifies,
and deletes a uniquely named Weaviate collection. It does not touch the
project corpus or retained Compose volumes. Start services with `make up`
first; this check does not start or stop containers.

To stop the containers at any time, run:
```bash
make down
# Equivalent to: docker compose -f infra/docker-compose.yml down
```

---

## 5. Python Environment Setup

### Fresh CPU environment

The checked `requirements.lock.txt` lists 154 exact packages and selects CPU
Torch `2.15.0+cpu` from public PyPI/PyTorch CPU indexes. On a new clone with
no existing `.venv`, create and sync it with:

```bash
uv venv --python 3.12.15 .venv
uv pip sync --python .venv/bin/python requirements.lock.txt
uv pip check --python .venv/bin/python
```

For verification, the same commands used a temporary path to protect the
existing CUDA environment:

```bash
uv venv --python 3.12.15 /tmp/news-intel-cpu-verification
uv pip sync --python /tmp/news-intel-cpu-verification/bin/python requirements.lock.txt
uv pip check --python /tmp/news-intel-cpu-verification/bin/python
```

The fresh environment passed dependency consistency and FastAPI, Scrapy and
CPU Torch imports. CPU model inference and the full test suite were not run.
The observed uv version was `0.8.23`; it is not pinned by the repository.

### Existing CUDA environment

The active `.venv` was preserved and uses Python `3.12.11` with Torch
`2.15.0+cu132`. The CPU lock does not recreate this CUDA installation. Do not
sync the CPU lock or install CPU Torch into the working CUDA environment. A
fresh CUDA setup needs a separately verified compatible Torch build; the
committed lock does not provide one.

`models.device` in `config/default.yaml` selects API inference (`cuda` by
default; code supports `cpu`). `scripts/verify_models.py` also accepts
`--device cpu` or `--device cuda` for an explicit model smoke. To run the API
on CPU, set `models.device: cpu` in the local config before startup, then
restore the previous value when returning to the CUDA setup.

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
On the development machine, real inference passed on an RTX 3050 Ti with CUDA
fp16: BGE-M3 returned two finite 1,024-dimensional vectors and the
cross-encoder returned two finite scores in 7.63 seconds using about 1,085
MiB. This verifies model execution and output validity, not retrieval
relevance or ranking quality. Run models in separate processes to keep their
memory use sequential.

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
supported workflow below. Do not run `make index`, `make cluster` or `make eval`
as if they produced validated research results.

### 6.1 Freeze and index the approved corpus

The snapshot builder reads only `news_intel_corpus_v1`; it writes immutable
JSONL/manifest files under `data/snapshots/<snapshot-id>/` and inserts an
insert-only manifest in that database's `corpus_snapshots` collection. It
does not modify campaign article/raw records, legacy database `news_intel`, or
old local artifacts. It inserts the snapshot manifest into the campaign
database. The current snapshot contains 516 articles and 2,135 chunks.

```bash
.venv/bin/python -m core.snapshot --self-check
.venv/bin/python -m core.snapshot
```

The second command prints the deterministic snapshot ID, counts and manifest
hash. Rebuilding identical inputs verifies the existing files and manifest;
different content under the same ID is refused. For current data the ID is
`corpus-59b2b589fe3bbdbffdc3`. To build and verify its dedicated Weaviate
collection without changing the active config, run:

```bash
.venv/bin/python -m core.snapshot_index --snapshot-id corpus-59b2b589fe3bbdbffdc3
```

Only after the command succeeds, activate the verified index:

```bash
.venv/bin/python -m core.snapshot_index --snapshot-id corpus-59b2b589fe3bbdbffdc3 --activate
```

The indexer verifies chunk count, provenance and each stored vector before
activation. It uses a snapshot-specific collection and does not drop the
previous collection. If a build or verification fails, leave the current
active configuration in place; rerun the same command after resolving the
failure. To deliberately make a verified snapshot active, rerun with
`--activate`. The Make shortcut `make index-snapshot
SNAPSHOT_ID=corpus-59b2b589fe3bbdbffdc3` also builds, verifies and activates.

Current artifacts are local and ignored by Git. Keep the snapshot files and
their checksums together for replay. This index gate verifies construction and
provenance, not retrieval quality. Do not share raw article text or images.

For the current demo, use the existing snapshot and index; do not rebuild or
activate an index just to present. Required snapshot identity and checksums
are in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).

### 6.2 Generate and compare snapshot topics

The topic runner accepts only the configured active snapshot. It verifies the
snapshot and cached chunk-embedding metadata/checksum, averages each article's
chunk embeddings and L2-normalizes the result, then fits BERTopic on title plus
body text. It does not re-embed articles. A successful run writes immutable
artifacts under
`data/topic_runs/<snapshot-id>/<settings-hash>/<run-id>/` and atomically updates
`data/topic_runs/active.json` only after both artifacts are written. A failure
before activation leaves the prior pointer in place. Keep the snapshot,
embedding files, run artifacts and active pointer together to inspect or serve
the same results.

To create a new real topic run:

```bash
.venv/bin/python -m core.snapshot_topics --snapshot-id corpus-59b2b589fe3bbdbffdc3
```

This performs BERTopic/UMAP/HDBSCAN computation; it is not a cached result
lookup. The recorded run was CPU-only and took 10.37 seconds with BERTopic
0.17.4, UMAP 0.5.12, HDBSCAN 0.8.44, NumPy 2.5.4 and scikit-learn 1.9.1.
Its fixed settings include seed 42, UMAP cosine distance with 15 neighbors and
5 components, and HDBSCAN minimum cluster size 15 and minimum samples 5.

The comparison baseline uses character TF-IDF (2–5 grams, at most 200,000
features) and six-cluster KMeans (seed 42, ten initializations) on the same
article title/body text. `--baseline-only` writes its immutable saved artifact;
`--compare` reads that artifact plus the checksum-verified active BERTopic run
and writes their comparison alongside the baseline. The comparison verifies
snapshot manifest, article ordering, chunks, embedding and active run checksums
before calculating metrics. It scores the single primary publisher-section
category as a weak label, not verified topic truth.

```bash
.venv/bin/python -m eval.snapshot_topics --self-check
.venv/bin/python -m eval.snapshot_topics --baseline-only --snapshot-id corpus-59b2b589fe3bbdbffdc3
.venv/bin/python -m eval.snapshot_topics --compare --snapshot-id corpus-59b2b589fe3bbdbffdc3
```

The saved run has 11 non-outlier topics and 17 outliers among 516 articles.
See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for saved run IDs,
metrics, denominators, per-language values and limitations. Topic artifact
generation does not write generic article/cluster records to MongoDB.

### 6.3 Run the snapshot retrieval evaluation

The retrieval evaluation requires the active frozen snapshot and its verified
Weaviate index. It runs real BM25, dense BGE-M3, and hybrid rankings; it does
not generate relevance labels. The committed query file and freeze record bind
the runs to snapshot `corpus-59b2b589fe3bbdbffdc3` and the frozen 60-query set.
Use the saved runs and pool when continuing the current experiment:

```bash
make eval-retrieval ACTION=validate
make eval-retrieval ACTION=run
make eval-retrieval ACTION="run --split dev --output artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/dev_baseline.json"
make eval-retrieval ACTION="pool --run artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json"
make eval-retrieval ACTION="score --run artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json --pool artifacts/retrieval_eval/v1/pools/corpus-59b2b589fe3bbdbffdc3/pool.json --judgments data/retrieval_eval/corpus-59b2b589fe3bbdbffdc3/judgments.jsonl"
```

The default run is held-out `test`; development is run separately and does not
change settings. Pooling writes a blinded short-excerpt judging packet to
ignored local `data/retrieval_eval/`. Do not redistribute article text or
images. The default score command writes `status: incomplete` and
`metrics: null` until real human judgments are supplied at
`data/retrieval_eval/corpus-59b2b589fe3bbdbffdc3/judgments.jsonl`. The packet,
rubric, annotation schema, and current counts are documented in
[retrieval_evaluation.md](retrieval_evaluation.md). Do not use `make eval` for
this workflow; that target is a disabled legacy evaluation entrypoint.

---

## 7. Starting the FastAPI Backend

Launch the asynchronous FastAPI application using Uvicorn:

```bash
make api
# Runs .venv/bin/python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

That Slice 06 API smoke did not evaluate the browser UI or retrieval quality.
Separate Slice 08 browser checks passed against the active snapshot, but
retrieval relevance remains unevaluated on a judged dataset. The Slice 06
smoke covered all three search modes and the summary route's explicitly
unavailable provider response; no summary generation or account access was
tested. See the [API reference](api_reference.md) for response fields and
failure states.

### API readiness and health

`make api` starts uvicorn through `.venv/bin/python`, bound to
`127.0.0.1:8000`. Check root readiness and database health:

```bash
curl -i http://localhost:8000/
curl -i http://localhost:8000/api/health
```

The verified startup returned HTTP 200 with root status `ready` and health
status `ok` (`mongodb: true`, `weaviate: true`). The root route checks
embedding/index readiness; `/api/health` checks MongoDB and Weaviate. These
responses do not certify retrieval quality or end-to-end UI behavior.

Example health body:
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

## Faculty demo rehearsal

The recorded 13 November rehearsal used this configured local environment and
existing MongoDB/Weaviate services. First ensure the local snapshot and topic
artifacts are present, start API with `make api`, then start the frontend in a
second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. Verify API readiness and database health:

```bash
curl -i http://localhost:8000/
curl -i http://localhost:8000/api/health
```

Demo Search → cross-language results → original publisher URL → Topics →
Corpus → the measured latency table in
[VERIFICATION_REPORT.md](VERIFICATION_REPORT.md). The rehearsal query was
`test-en-05`: “Find Hindi coverage explaining why October inflation crossed
the central bank’s tolerance ceiling.” Search's optional summary should show
provider access unverified. The rehearsal's publisher URL returned HTTP 200,
but external availability can change. A Playwright 503 screen was simulated
with request interception; no service was stopped. The full flow and scratch
recovery details are in the runtime rehearsal record. This is not a fresh
clone/full-pipeline test.

---

## 8. Starting the Next.js Frontend

In a new terminal window, navigate to the `frontend/` directory, install packages, and launch the Next.js development server:

```bash
cd frontend
npm ci
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

Open **[http://localhost:3000](http://localhost:3000)**. The workspace has three
routes: Search, Topics, and Corpus. Search queries the active frozen snapshot;
Topics reads the saved topic run; Corpus reports snapshot coverage. The bounded
browser review passed at desktop and 390px mobile widths. See the
[frontend guide](frontend_guide.md) for route behavior, screenshots, empty and
unavailable states, and research limits. Chat and credibility are not part of
this workspace.

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
experience. See the verification report for which bounded gates passed and
the remaining human-judgment and release checks.

### 9.2 Legacy evaluation entrypoints

The old evaluation entrypoints, including `make eval`, are intentionally
disabled because their generated outputs are not valid evidence for this
project. Do not run them or use the existing ignored result files in a report.
For clustering, use the snapshot-scoped `eval.snapshot_topics` commands in
section 6.2 and cite its saved artifacts. Those results compare clustering to
publisher-section weak labels; they do not establish factual topic truth.
For retrieval, use `make eval-retrieval` as described in section 6.3. The
saved held-out run and blinded pool are ready for annotation, but its score
remains incomplete until human judgments pass the documented coverage,
double-judgment, and adjudication requirements. BM25, dense and hybrid also
passed API behavior smoke checks against the active frozen snapshot, and the
Search/Topics/Corpus browser gate passed against real services. The plan
specifies minimal, risk-targeted checks for each implementation slice; broad
duplicate test runs are not required.

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
