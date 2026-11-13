# Multilingual News Intelligence Platform

An NLP course project exploring whether multilingual retrieval can help readers find Indian news across English, Hindi, Bengali and Marathi, and whether topic clustering can make a collected corpus easier to explore.

**Status: active research project; the bounded Ask review reached its eight-call cap, and final user acceptance is pending.** Five full app answers, one unsupported-question abstention, and one partial answer with an explicit gap were independently checked against saved passages and citation provenance. Examples covered English, Hindi, Bengali and Marathi; one English answer cited Bengali-only evidence. A genuine conflicting-source example was not identified. This small sample does not establish answer quality or runtime semantic support. Slice 09 retrieval engineering passed but its quality gate is unmet: 427 pooled query/article pairs have no human judgments, so its score has null metrics. The isolated campaign contains 516 accepted articles, 586 raw versions and 66 rejected raw versions. The active snapshot has a provenance-checked Weaviate index and the workspace presents Search, Ask, Topics and Corpus. These counts are not representative or quota-complete. Topic comparison measures agreement with weak publisher-section labels, not truth or event coherence. See the [retrieval evaluation protocol](docs/retrieval_evaluation.md), [overhaul roadmap](docs/OVERHAUL_PLAN.md), [presentation runbook](docs/presentation_guide.md) and [verification record](docs/VERIFICATION_REPORT.md).

## Research focus

Compare lexical BM25, multilingual dense retrieval and hybrid retrieval on a documented, frozen news corpus. Explore clustering as a way to browse that corpus. The academic contribution should be the data collection, evaluation design, results and limitations—not an unverified claim that a model works well. Credibility scoring, misinformation detection and fabricated verification badges are out of scope.

## Verified so far

- Eight selected source-language Scrapy adapters completed bounded live runs. The final isolated campaign contains 516 accepted records; publisher-section categories are weak labels, environment coverage is absent, and near-duplicate/syndication checks remain incomplete.
- MongoDB and Weaviate containers passed their bounded readiness checks.
- BGE-M3 embedding and cross-encoder reranker ran on the available CUDA GPU and returned finite outputs. This verifies inference only, not ranking quality.
- Frozen snapshot `corpus-59b2b589fe3bbdbffdc3` contains 516 articles and 2,135 chunks; its dedicated Weaviate index passed full provenance and vector readback. This verifies index construction, not retrieval quality.
- BM25, dense, and hybrid each ranked the 48 frozen held-out queries once, plus a separate 12-query development run. Their union contains 427 distinct query/article pairs; human judgments are still pending, so no relevance score is claimed. See the [evaluation guide](docs/retrieval_evaluation.md).
- The API distinguishes valid empty results from unavailable dependencies; Ask sends the original question and validated retrieved passages to generation and checks citation IDs and snapshot provenance. The prompt instructs the model to use the passages; runtime semantic claim support is not guaranteed.
- Search, Topics, Corpus and Ask passed the documented frontend gates, including a 390px browser check for Ask, keyboard citation navigation, reduced-motion handling and escaped passage text. Five bounded live answers passed independent passage/citation review; final user acceptance remains pending. See the [verification record](docs/VERIFICATION_REPORT.md).
- The 13 November local rehearsal verified a cross-language Search query, HTTP 200 for its original source, and recovery of 2,135 cached vectors into a scratch Weaviate collection without activation or re-embedding. Its former summary-unavailable check is historical; Playwright's 503 screen was intercepted and simulated. No service was stopped. This is not a fresh-clone/full-pipeline rehearsal.

Detailed counts, commands and limitations are in [docs/VERIFICATION_REPORT.md](docs/VERIFICATION_REPORT.md). Current implementation and remaining work are tracked in [docs/OVERHAUL_PLAN.md](docs/OVERHAUL_PLAN.md).

## Current API behavior

- `POST /api/search`: supports `hybrid`, `dense` or `bm25`; valid searches with no matches return `200` and an empty `results` list. Missing retrieval dependencies return `503`.
- `POST /api/ask`: accepts one question and returns claim-linked answer segments with server-resolved citations, or an explicit insufficient-evidence, generation-unavailable or evidence-integrity status. It uses up to 30 hybrid candidates and at most 8 provenance-checked passages; see the [API reference](docs/api_reference.md).
- `GET /api/corpus`: reports snapshot-backed corpus coverage. Topic counts include the `-1` outlier group when a verified topic run is active; crawl/rejection metadata remain explicitly unavailable where they cannot be linked to the immutable snapshot.
- `GET /api/clusters`: returns topics from the verified active-snapshot artifact, including an empty list when no run exists. Unknown topic IDs return `404`; invalid or unavailable snapshot/topic artifacts return `503`.
- `GET /api/health`: reports `ok` only when MongoDB and Weaviate are reachable; otherwise it reports `degraded`.

Search responses include ranked unique articles and top-level execution metadata. See the [API reference](docs/api_reference.md) for request/response shapes and failure states.

## Local development

Requirements: Python 3.12.15 for the checked CPU lock, Node.js supported by the installed Next.js version, Docker Compose, local snapshot/topic artifacts, and model weights for dense search. The checked fresh CPU dependency install/import gate passed, but a fresh clone, CPU model inference, and full collection-to-demo pipeline were not tested. The existing CUDA environment is separate and should not be overwritten by syncing that lock. See [setup.md](docs/setup.md).

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
- [Frontend guide](docs/frontend_guide.md)
- [API reference](docs/api_reference.md)
- [Verification report](docs/VERIFICATION_REPORT.md)
- [Full phased roadmap](docs/OVERHAUL_PLAN.md)
