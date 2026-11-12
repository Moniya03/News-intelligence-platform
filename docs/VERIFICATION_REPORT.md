# Runtime verification report

Date: 13 November 2026
Scope: local MongoDB/Weaviate readiness, real local model inference, and a bounded live spider-to-Mongo pilot. This does not certify the full overhaul, a research corpus, retrieval quality, or production-wide source coverage.

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| MongoDB | PASS | Compose service `mongo:7` (observed MongoDB 7.0.45) started. Isolated read-after-write succeeded in `news_intel_verification.smoke_checks`; the unique smoke record was removed. |
| Weaviate | PASS | Compose service started; readiness returned HTTP 200 (version 1.27.3). A uniquely named collection passed vector write/read and was deleted. |
| BGE-M3 embedder | PASS | Real FlagEmbedding backend on RTX 3050 Ti CUDA, fp16. Two multilingual vectors were finite and 1,024-dimensional; approximately 4.4 seconds. |
| BGE cross-encoder reranker | PASS | Real CrossEncoder backend on RTX 3050 Ti CUDA, fp16. Two finite scores; approximately 7.9 seconds and 1,083 MiB allocated. |
| Scrapy-to-Mongo pilot | PASS (bounded gate) | Independent review passed the eight latest live runs, Mongo raw/current references, quarantine audit, and lifecycle test. This verifies the bounded ingestion path, not production-wide coverage or corpus quality. See details below. |
| OpenAI summary provider | NOT TESTED | No account-access request was made. Rotate/revoke any active key that appeared in tool output before use. |

The model checks establish execution and output validity only. They do not measure retrieval relevance, ranking quality, summary quality, or API account entitlement.

## Truthfulness and preservation gates (13 November 2026)

Independent Slice 00 reviews passed the focused backend/retrieval and evaluation-safety checks, plus frontend checks (15 Node tests, lint, production build and production dependency audit with zero findings). The development dependency audit reported seven moderate findings. The reviewers also checked readiness behavior with dependency stubs: missing embedding/index dependencies report degraded readiness; configured usable dependencies report ready. This is bounded implementation verification, not a populated-index or end-to-end research acceptance result. These gates were run by the independent implementation reviewers; this report update does not claim they were rerun here.

The updated API returns valid empty search/topic results as empty responses, reports unavailable dependencies as errors, and does not fabricate article, topic or chat fallback content. Legacy generated evaluation entrypoints are disabled, and the legacy loader refuses the configured application database. Existing ignored datasets and result artifacts were preserved; they are not certified as the new corpus or valid experimental results. The full corpus, indexed search quality, topic evaluation and UI acceptance remain incomplete. See [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md) for slice status and remaining acceptance criteria.

## Slice 01 runtime gate (13 November 2026)

The clean CPU dependency environment used mise Python 3.12.15 and uv 0.8.23 (observed versions, not pinned). `requirements.lock.txt` contains 154 exact package pins and resolves Torch `2.15.0+cpu` from the public PyPI and PyTorch CPU indexes. In `/tmp/news-intel-cpu-verification`, dependency sync, `uv pip check --python /tmp/news-intel-cpu-verification/bin/python`, and FastAPI, Scrapy and Torch imports passed. The active CUDA `.venv` was left unchanged; it uses Python 3.12.11 and Torch `2.15.0+cu132`. The CPU lock does not recreate CUDA Torch, and CPU model inference was not run.

In the existing CUDA environment, independent verification passed real BGE-M3 embedding inference and reranker inference on an RTX 3050 Ti. The embedding check returned two finite 1,024-dimensional vectors; the reranker returned two finite scores in 7.63 seconds using approximately 1,085 MiB. This verifies runtime execution only.

`make infra-smoke` passed MongoDB read-after-write with cleanup and Weaviate readiness plus an isolated collection vector write/read/delete round trip. Compose services used local ports and retained their volumes. `make api` started through `.venv/bin/python` and bound uvicorn to `127.0.0.1:8000`; root readiness returned HTTP 200 `ready` and `/api/health` returned HTTP 200 with both database services true. Retrieval/index quality, browser UI behavior, CPU inference and full application acceptance remain unverified. The shutdown emitted a Python resource-tracker semaphore warning after successful checks; it did not change their outcomes.

Independent review passed fresh-CPU dependency/import checks and lock consistency. No full test suite or browser run was performed for this gate. The commands and environment caveats are in [setup.md](setup.md).

## Bounded Scrapy-to-Mongo pilot (12 November 2026 UTC)

The live crawl and database audit used the local Scrapy project and `news_intel` Mongo database. Latest successful run records are dated 12 November UTC (18:16–18:42); counts below are request/article outcomes, not unique stories across publishers. The mapping versions were `global-category-v2`, except Amar Ujala's final corrected run, which used `global-category-v3`.

| Adapter | Fetched | Accepted | Rejected | Errors | Current articles | P | F | H | ST | E | S |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ABP English | 10 | 10 | 0 | 0 | 10 | 2 | 2 | 2 | 2 | 0 | 2 |
| ABP Hindi | 10 | 10 | 0 | 0 | 10 | 0 | 3 | 3 | 1 | 0 | 3 |
| ABP Bengali | 10 | 9 | 1 | 0 | 9 | 1 | 2 | 2 | 2 | 0 | 2 |
| ABP Marathi | 10 | 9 | 1 | 0 | 9 | 3 | 2 | 0 | 1 | 0 | 3 |
| OneIndia English | 14 | 14 | 0 | 1 | 14 | 0 | 5 | 4 | 0 | 0 | 5 |
| Amar Ujala Hindi | 12 | 6 | 6 | 0 | 6 | 0 | 0 | 2 | 0 | 0 | 4 |
| News18 Bengali | 20 | 20 | 0 | 0 | 20 | 0 | 10 | 0 | 0 | 0 | 10 |
| Loksatta Marathi | 16 | 16 | 0 | 0 | 16 | 4 | 4 | 4 | 0 | 0 | 4 |
| **Total** | **102** | **94** | **8** | **1** | **94** | **10** | **28** | **17** | **6** | **0** | **33** |

Category abbreviations: P politics, F finance, H health, ST science/technology, E environment, S sports. Counts reflect accepted article-section mappings in this bounded sample. An adapter/category zero means no accepted article was observed in this run; it does not prove a publisher has no such section. In particular, Loksatta has a configured environment route but zero accepted environment articles here. No environment coverage was observed. The observed labels come from source-section mappings, are weak labels rather than verified article themes, and must not be treated as a balanced or representative corpus.

OneIndia's single spider error was a candidate under `/partner-content/`; the source's robots.txt explicitly disallows that path for the exact crawler user agent, so it was not fetched or bypassed. Loksatta sports included an editorial item that may be sports-section noise. Some ABP science/technology pages republished DW reporting; canonical source attribution and syndication deduplication remain future corpus-quality work. These checks establish a bounded ingestion path, not editorial accuracy or source independence.

The database snapshot contained 94 current adapter articles, 242 raw-version records across this campaign's history, and 18 quarantined adapter records. Quarantined records retain raw references and are excluded from the current adapter article set. The bounded pilot had no validated live article with multiple mapped categories; multi-section merge behavior was covered only by synthetic lifecycle data. Do not claim real multi-topic article coverage from this pilot.

Run a bounded adapter crawl from the repository root with the project's environment:

```bash
SCRAPY_SETTINGS_MODULE=scrapers.settings .venv/bin/python -m scrapy crawl abp_en -a max_articles=10 -s MONGO_DATABASE=news_intel -s LOG_LEVEL=WARNING
```

Replace `abp_en` with one of `abp_hi`, `abp_bn`, `abp_mr`, `oneindia_en`, `amarujala_hi`, `news18_bn`, or `loksatta_mr`. The source registry and explicit section/category mappings are in [`scrapers/sources.py`](../scrapers/sources.py). A higher `max_articles` bounds request-section pairs, so duplicate canonical URLs encountered in more than one mapped section can merge into one current article.

## Reproduction

Start local services, then run the isolated infrastructure check:

```bash
make up
make infra-smoke
```

With the project Python environment active and the model weights available, run each model separately so one model is released before loading the other:

```bash
python scripts/verify_models.py embedder
python scripts/verify_models.py reranker
```

Focused reranker and syntax checks:

```bash
python -m unittest tests.test_rerank -v
python -m py_compile infra/smoke_test.py scripts/verify_models.py core/rerank.py
git diff --check
```

The infrastructure smoke uses `news_intel_verification`, removes only its own temporary record, and leaves Compose volumes and corpus data untouched. The model smoke exits unsuccessfully if the configured real backend is unavailable or CUDA is explicitly requested but unavailable.

## Review

An independent reviewer reran `make infra-smoke`, the focused model test, model compilation, and both model smokes on CUDA. All passed. The reviewer found no blocking issues. The reranker now requests fp16 weights during CUDA loading; converting after a full-precision load had exhausted available GPU memory and caused the wrapper to fall back to lexical scoring.

Independent scraper review passed: 10 scraper unit tests, the Mongo lifecycle test, all eight registered spiders (`scrapy list`), compilation and diff checks, plus an independent three-article ABP English run in an isolated Mongo database with raw and normalized records verified. The reviewer audited all 94 current adapter records, their raw references and section contexts, and all 18 quarantined records; no stale v1 or Amar v2 current records remained. The OneIndia robots-denied candidate was independently confirmed as an expected `IgnoreRequest`, not a transport or extraction failure. This passes the bounded integration gate only. It does not establish broad publisher reliability, topic truth, independent reporting, complete category coverage, or a representative research corpus.
