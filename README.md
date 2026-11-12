# Multilingual News Intelligence Platform

An NLP course project exploring whether multilingual retrieval can help readers find Indian news across English, Hindi, Bengali and Marathi, and whether topic clustering can make a collected corpus easier to explore.

**Status: active rebuild; not yet a complete research demonstration.** The project has a bounded live Scrapy-to-Mongo pilot and verified local model execution. The current corpus is too small and uneven to support retrieval-quality or clustering claims, and a complete indexed end-to-end demo has not been verified. See the [overhaul roadmap](docs/OVERHAUL_PLAN.md) and [verification record](docs/VERIFICATION_REPORT.md).

## Research focus

Compare lexical BM25, multilingual dense retrieval and hybrid retrieval on a documented, frozen news corpus. Explore clustering as a way to browse that corpus. The academic contribution should be the data collection, evaluation design, results and limitations—not an unverified claim that a model works well. Credibility scoring, misinformation detection and fabricated verification badges are out of scope.

## Verified so far

- Eight selected source-language Scrapy adapters completed bounded live runs and stored raw and normalized records in MongoDB. This is a pilot, not representative coverage or a validated research corpus.
- MongoDB and Weaviate containers passed their bounded readiness checks.
- BGE-M3 embedding and cross-encoder reranker ran on the available CUDA GPU and returned finite outputs. This verifies inference only, not ranking quality.
- The API now distinguishes valid empty results from unavailable dependencies; it does not return demo search/chat content when a provider or index is unavailable.

Detailed counts, commands and limitations are in [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md). Current implementation and remaining work are tracked in [docs/OVERHAUL_PLAN.md](docs/OVERHAUL_PLAN.md).

## Current API behavior

- `POST /api/search`: supports `hybrid`, `dense` or `bm25`; valid searches with no matches return `200` and an empty `results` list. Missing retrieval dependencies return `503`.
- `POST /api/chat`: answers only from retrieved evidence with explicit citations. No matches return a no-evidence response; unavailable retrieval or answer generation returns an error instead of invented content.
- `GET /api/clusters`: returns stored topics, including an empty list when none exist. Unknown topic IDs return `404`; unavailable topic storage returns `503`.
- `GET /api/health`: reports `ok` only when MongoDB and Weaviate are reachable; otherwise it reports `degraded`.

See [API reference](docs/api_reference.md) for request and response shapes.

## Local development

Requirements: Python 3.12.15 for the checked CPU lock, Node.js supported by the installed Next.js version, Docker Compose, and model weights for local inference. `uv 0.8.23` was observed during verification; it is not pinned. The checked lock installs CPU Torch. The existing CUDA environment is separate and should not be overwritten by syncing that lock.

```bash
cp .env.example .env
make up
make infra-smoke
```

For a fresh CPU environment, sync the exact lock before starting services:

```bash
uv venv --python 3.12.15 .venv
uv pip sync --python .venv/bin/python requirements.lock.txt
make api
```

For a verified fresh-install command and the preserved CUDA setup, see
[docs/setup.md](docs/setup.md). The CPU lock does not recreate CUDA Torch.

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The frontend expects `NEXT_PUBLIC_API_URL=http://localhost:8000` (for example in `frontend/.env.local`). Setup and verification details are in [docs/setup.md](docs/setup.md).

**Do not run the legacy ingestion/evaluation scripts against the application database or treat their existing result files as valid measurements.** The legacy dataset loader now requires an explicitly isolated database; the old generated evaluation entrypoints are disabled. See the roadmap before attempting corpus or index work.

## Project documents

- [Problem statement](docs/problem_statement.md)
- [Project purpose](docs/project_purpose.md)
- [Architecture and current status](docs/architecture.md)
- [Faculty presentation guide](docs/presentation_guide.md)
- [Setup](docs/setup.md)
- [API reference](docs/api_reference.md)
- [Verification report](docs/VERIFICATION_REPORT.md)
- [Full phased roadmap](docs/OVERHAUL_PLAN.md)
