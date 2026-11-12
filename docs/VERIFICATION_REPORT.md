# Runtime verification report

Date: 13 November 2026
Scope: local MongoDB/Weaviate readiness, real local model inference, an earlier bounded spider-to-Mongo pilot, the isolated 90-day corpus campaign, Slice 06 search/API behavior, and Slice 07 topic artifacts/API behavior. This does not certify the full overhaul, retrieval quality, publisher permission, or production-wide source coverage.

## Results

| Area | Result | Evidence |
| --- | --- | --- |
| MongoDB | PASS | Compose service `mongo:7` (observed MongoDB 7.0.45) started. Isolated read-after-write succeeded in `news_intel_verification.smoke_checks`; the unique smoke record was removed. |
| Weaviate | PASS | Compose service started; readiness returned HTTP 200 (version 1.27.3). A uniquely named collection passed vector write/read and was deleted. |
| BGE-M3 embedder | PASS | Real FlagEmbedding backend on RTX 3050 Ti CUDA, fp16. Two multilingual vectors were finite and 1,024-dimensional; approximately 4.4 seconds. |
| BGE cross-encoder reranker | PASS | Real CrossEncoder backend on RTX 3050 Ti CUDA, fp16. Two finite scores; approximately 7.9 seconds and 1,083 MiB allocated. |
| Scrapy-to-Mongo pilot | PASS (bounded gate) | Independent review passed the eight latest live runs, Mongo raw/current references, quarantine audit, and lifecycle test. This verifies the bounded ingestion path, not production-wide coverage or corpus quality. See details below. |
| Isolated corpus campaign | PASS (collection and read-only audit) | Campaign `corpus-20261112T194939Z` contains 516 accepted current records, 586 raw versions and 66 rejected raw versions in `news_intel_corpus_v1`; details and limitations below. |
| Slice 07 topics and baseline | PASS (focused gate) | Real BERTopic and fixed TF-IDF/KMeans artifacts match the frozen snapshot; focused topic/API checks, metric/provenance self-check, saved comparison, compilation, diff check and read-only API checks passed. Results are weak-label agreement, not verified truth. |
| Summary generation/provider access | NOT TESTED | The Slice 06 route returned its unavailable state; no model call or account-access request was made. Rotate/revoke any active key that appeared in tool output before use. |

The model checks establish execution and output validity only. They do not measure retrieval relevance, ranking quality, summary quality, or API account entitlement.

## Slice 05 frozen snapshot and index gate (13 November 2026)

Snapshot `corpus-59b2b589fe3bbdbffdc3` was built from the isolated
`news_intel_corpus_v1` database. It contains 516 articles and 2,135 chunks:
English 123, Hindi 116, Bengali 156 and Marathi 121. The canonical manifest
SHA-256 is
`0c56de1aafcbd32d19e68f8c0b99f2f31f1f5c5e89a49cbeae20acf416bb5eb2`; the
chunks SHA-256 is
`db3f0a1727b264f5c73df330e407ea3468f34c812d3b36d94b76e3fd7b303c16`. A
prior snapshot `corpus-d269b8db17b1f3b0812e` remains intact and was not
activated; it has a different schema/identity after the required
`source_adapter` provenance correction.

Reproduction and activation commands from the repository root:

```bash
.venv/bin/python -m core.snapshot --self-check
.venv/bin/python -m core.snapshot
.venv/bin/python -m core.snapshot_index --snapshot-id corpus-59b2b589fe3bbdbffdc3
.venv/bin/python -m core.snapshot_index --snapshot-id corpus-59b2b589fe3bbdbffdc3 --activate
```

The snapshot builder deterministically writes local `articles.jsonl`,
`chunks.jsonl`, and `manifest.json`, then inserts an immutable manifest into
`news_intel_corpus_v1.corpus_snapshots`. Existing data under an ID is verified
and never replaced. Article/chunk/full-text artifacts remain local and
ignored; legacy database `news_intel` and prior local artifacts were untouched.
Snapshot IDs pin the selected article versions, raw-version references,
chunking and checksums. The eight adapters yielded language counts above and
category counts from the campaign; categories remain section-derived weak
labels, with zero environment articles.

The dedicated Weaviate collection is
`NewsChunkSnapshotdcc85b7d4a2e9122136846f3874bca65af0ce6d0`. The cached
BGE-M3 revision was `5617a9f61b028005a4858fdac845db406aefb181`, using CUDA
fp16 on an RTX 3050 Ti with batch size 4. Initial inference and indexing took
about 1 minute 27 seconds; no peak-memory measurement was taken. Full count
and provenance readback passed. The later required 200-object paged readback
matched all 2,135 chunk IDs and vectors exactly to the cached embeddings
(maximum absolute error 0). A cache-reuse verification/re-activation run took
about 7 seconds.

The initial implementation activated the collection before completing the
required stored-vector readback. The corrected implementation added that
verification; a cache-reuse run completed full ID/provenance/vector readback,
then reactivated. The current implementation verifies readback before
activation; the initial sequence is a process deviation, not gated evidence.
Older pointers and collections were preserved; no destructive drops occurred.

Independent final checks passed: eight focused snapshot-index/retrieval tests,
Python compilation of three modules, snapshot self-check, `git diff --check`,
and full vector readback. No full suite, lint, or model re-inference was run.
The active config points to this snapshot, database and collection. This gate
proves reproducible artifacts and index provenance, not ranking quality,
representativeness, publisher permission, editorial truth, or Slice 06 API
response extensions.

## Slice 06 search, summary, and corpus API gate (13 November 2026)

Independent review passed the search, corpus, and summary route changes. Focused checks passed 22 backend/retrieval tests and 3 API tests; Python compilation and `git diff --check` also passed. A sequential API smoke returned HTTP 200 for BM25, dense, and hybrid searches with two results each, the active snapshot ID, and matching requested/executed modes. Dense and hybrid used real cached BGE-M3 query embeddings. The reviewer separately verified BM25 filtering and serialization with `lang_filter: ["en"]`: three unique articles included HTTPS URLs, publication dates and the active snapshot; metadata reported `requested_mode` and `executed_mode` as `bm25`, numeric elapsed time, and `reranker_status: "disabled"`. No GPU/model was loaded for this independent check.

The same API smoke checked `/api/corpus` (`200`), `/api/search/summary` (`200`, provider unavailable), a stale summary snapshot (`409`), and a blank search query (`422`). Search results are unique articles with snapshot provenance and top-level metadata. The configured local reranker was not exercised in this API run; actual reranker inference was verified separately in Slice 01, while Slice 06 checked the truthful disabled/unavailable and failure-preserves-base-order behavior. No additional model inference was run for this slice.

`GET /api/corpus` reads and verifies local immutable snapshot files. For `corpus-59b2b589fe3bbdbffdc3` it reports 516 articles, 2,135 chunks, languages English 123, Hindi 116, Bengali 156 and Marathi 121, with eight source adapters and snapshot coverage. Index `collection_status: "configured"` describes configuration, not live health. `topic_counts` remains null and `topic_status` is `not_generated`. Crawl timestamp and rejection count remain null because the frozen manifest/raw references do not contain immutable crawl-run links; the separate campaign report still records 66 rejected raw versions.

`POST /api/search/summary` validates distinct article IDs and active snapshot provenance. Usable evidence returns citations but `status: "unavailable"` with `reason: "provider_access_unverified"`; article bodies shorter than 200 characters are not cited, and no usable bodies yield `insufficient_evidence`. The threshold checks text sufficiency, not factual or relevance support. No summary credentials/account access or summary-model call was tested. Search remains independent of optional summary generation.

## Slice 07 topic and baseline gate (13 November 2026)

The saved run used frozen snapshot `corpus-59b2b589fe3bbdbffdc3` (516 articles, 2,135 chunks) and its verified cached chunk embeddings. Article vectors were computed as mean chunk embeddings followed by L2 normalization; this run did not re-embed articles or download model weights. BERTopic ran on CPU in 10.37 seconds. Run ID is `bertopic-20261112T205209237980Z-177ffa64`, settings hash `e951dfc7368663d8558b32de9e694e223829cf6ccedeb46d8c351db01c029d98`. The persisted versions are BERTopic 0.17.4, UMAP 0.5.12, HDBSCAN 0.8.44, NumPy 2.5.4 and scikit-learn 1.9.1. Settings: seed 42; UMAP 15 neighbors, 5 components, cosine metric, minimum distance 0, one job; HDBSCAN minimum cluster size 15 and minimum samples 5. It produced 11 non-outlier topics plus 17 outliers (3.29%), assigning all 516 articles exactly once.

The fixed baseline artifact is `tfidf-kmeans-9e807cf206bcf0ed-c518b482cb5d`: character TF-IDF 2–5 grams, 200,000 features, KMeans with six clusters, seed 42 and 10 initializations. A second fit produced identical assignments. Both artifacts are under `data/topic_runs/corpus-59b2b589fe3bbdbffdc3/`; the run and settings paths, active-pointer checksums, baseline input checksums, comparison, language/source concentration, and duplicate metadata are saved with them. The comparison verifies the frozen manifest/articles/chunks/embeddings and active BERTopic pointer/run checksums before scoring.

All 516 articles had a mapped primary publisher-section category in this snapshot. NMI, ARI and purity below use those single section labels as weak proxies; they do not measure factual truth, event coherence, or retrieval quality. BERTopic all-document metrics explicitly treat `-1` as one noise assignment; assigned-only metrics omit those 17 articles and use 499 articles. Rounded to three decimals:

| Method / denominator | N | NMI | ARI | Purity |
| --- | ---: | ---: | ---: | ---: |
| TF-IDF/KMeans | 516 | 0.218 | 0.101 | 0.477 |
| BERTopic, with noise group | 516 | 0.678 | 0.674 | 0.909 |
| BERTopic, assigned only | 499 | 0.710 | 0.709 | 0.922 |

Per-language NMI / ARI (all-document BERTopic; baseline): Bengali 0.684 / 0.655 (0.467 / 0.365), English 0.829 / 0.790 (0.000 / 0.000), Hindi 0.667 / 0.654 (0.000 / 0.000), and Marathi 0.812 / 0.819 (0.499 / 0.332). Each uses the language's eligible primary-category articles: 156, 123, 116 and 121, respectively. The assigned-only BERTopic values and all per-cluster concentration details are in the saved comparison. Exact-body duplicate analysis found zero groups; near-duplicate and syndication detection was not performed. Category imbalance, source-section noise and corpus size limit interpretation. These measurements do not establish better or more meaningful topics.

The API reads only verified local topic artifacts: list provenance includes snapshot/run/settings/algorithm, `topic_count` counts non-noise topics, and `outlier_count` counts articles assigned `-1`. Detail includes the cluster metadata and paginated real snapshot articles. No run is an empty `200`; unknown topic is `404`; invalid or unavailable artifacts are `503`. The corpus summary exposes topic counts including `-1` and distinguishes `topic_status: "generated"`; crawl/rejection fields remain unavailable because immutable links to the snapshot are still absent. Focused Slice 07 checks passed (9 unit checks, metric/provenance self-check, saved-artifact comparison, compilation, diff check and read-only API checks); no broad suite or algorithm rerun was performed for this report.

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

## Isolated 90-day corpus campaign (12–13 November 2026 UTC)

The earlier 94-article adapter pilot above is historical and separate. The final bounded campaign, `corpus-20261112T194939Z`, wrote to isolated database `news_intel_corpus_v1`; it did not alter legacy database `news_intel`. Its UTC window was inclusive, 2026-08-16 through 2026-11-13. Each adapter run was capped at 150 article requests, 20 listing pages and 360 seconds. At most two runs ran concurrently, only for distinct publisher families; ABP adapters were serialized. No wider date window was needed or run.

The read-only quality audit found 516 accepted current articles, 586 raw versions, 66 rejected raw versions, no structural flags and no exact normalized-body duplicate groups. Rejections were 24 bodies under 200 characters, 12 missing publication dates, and 30 outside the inclusive date window. Near-duplicate and syndication detection is deferred, so zero exact duplicates does not mean zero related or republished stories. Unicode script ratios are plausibility checks, not language certification.

| Language | Accepted | Publisher-family counts |
| --- | ---: | --- |
| English | 123 | ABP 93; OneIndia 30 |
| Hindi | 116 | ABP 91; Amar Ujala 25 |
| Bengali | 156 | ABP 83; News18 73 |
| Marathi | 121 | ABP 85; Loksatta 36 |
| **Total** | **516** | **Eight configured adapters** |

| Category | Accepted articles |
| --- | ---: |
| politics | 63 |
| finance | 129 |
| health | 76 |
| science_technology | 80 |
| environment | 0 |
| sports | 168 |

These category counts reflect publisher section mappings, which are weak labels rather than verified article topics. No environment article was observed, and counts do not establish balanced or representative coverage. The aspirational corpus targets are 2,000 total, 500 per language and 250 per adapter. The former 1,000 total, 200 per language and 50 per publisher-family-per-language floors were explicitly relaxed to soft targets; the actual qualifying count is reported without quotas, padding, or a completeness claim.

The campaign and quality metadata are in [`artifacts/corpus_campaign/campaign.json`](../artifacts/corpus_campaign/campaign.json) and [`artifacts/corpus_campaign/quality_report.json`](../artifacts/corpus_campaign/quality_report.json). The audit is read-only and emits metadata only; it does not export raw article bodies. Reproduce with the project environment and MongoDB available:

```bash
SCRAPY_SETTINGS_MODULE=scrapers.settings .venv/bin/python scripts/collect_corpus.py --anchor 2026-11-13 --database news_intel_corpus_v1 --max-articles 150 --max-listing-pages 20 --timeout-seconds 360
SCRAPY_SETTINGS_MODULE=scrapers.settings .venv/bin/python scripts/audit_corpus.py --campaign artifacts/corpus_campaign/campaign.json --report artifacts/corpus_campaign/quality_report.json --sample-per-adapter 5
```

The interrupted first attempt stopped after an ABP family lock blocked one worker; its 42 accepted records and 50 raw versions were preserved. A separate settings-correction pilot accepted 33 records and was not mixed into the final campaign. The final metadata records only the completed campaign runs. Campaign limits are bounded crawl controls, not assurances that every publisher section or eligible article was discovered.

Collection success does not establish permission to automate collection, retain content indefinitely, or use it for ML. Policy URLs and unresolved terms/robots questions are recorded in [`source_access_notes.json`](../artifacts/corpus_campaign/source_access_notes.json). In particular, the recorded notes state that OneIndia terms restrict scraping and its configured transparent user-agent is not an allowed named search crawler; Amar Ujala terms restrict scraping and ML without written consent; and News18 policy/robots details could not be verified by the policy scout. ABP and Loksatta also have copying/automated-use restrictions described in the notes. Do not spoof, bypass, or redistribute raw article text or images. These source notes are not legal clearance.

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
