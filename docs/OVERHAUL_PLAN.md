# News Intelligence Platform: evidence-first NLP overhaul

Prepared: 12 November 2026. Status: approved plan; implementation and acceptance remain in progress.

The approved cited-Q&A design and implementation baseline is in [docs/design.md](design.md). It supersedes the earlier Search-summary/legacy-chat target; historical verification records below remain historical.

Current Ask status: focused API and frontend gates passed; after the first request failed during CUDA retrieval embedding, independent non-paid hybrid Search passed using CPU embeddings. Five full answers across EN/HI/BN/MR, one unsupported-question abstention, and one EN partial answer grounded in BN evidence passed independent review. No genuine conflict example was identified. The eight-call hard limit is reached; attempts 1 and 8 have unknown usage and retained reservations. Total reserved `$0.024`; known actual cost `$0.0015756` through attempt 7. This sample establishes neither answer quality nor runtime semantic support. Final user acceptance remains pending; see [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).

## 1. Outcome and scope

Build a presentable NLP course project answering this question: **Can multilingual embeddings help someone find reporting across Indian languages, and can topic clustering make that corpus easier to explore?** The demonstration must show real articles, their publishers and original URLs, reproducible retrieval comparisons, and honestly reported clustering results.

The project is salvageable. Keep its FastAPI, Next.js, MongoDB, Weaviate, BGE-M3, and BERTopic foundation. Replace the unreliable data path, fabricated success states, synthetic experiments, and crowded interface. A rewrite would spend the two-week window recreating infrastructure without solving those problems.

The contribution is a measured multilingual retrieval and topic-exploration pipeline, not a new foundation model or a misinformation detector. Pretrained models are acceptable; the academic work is corpus construction, baselines, experimental design, analysis, and limitations.

### Decisions already settled

| Area | Decision |
| --- | --- |
| Audience and deadline | College faculty first; portfolio second. Budget two weeks, with a final integration buffer. |
| Languages | English, Hindi, Bengali, Marathi. Keep language handling explicit rather than hardcoding the old Tamil assumptions. |
| Corpus | Target 2,000 accepted articles, approximately 500/language and 250/source-language adapter. Two publisher families per language. |
| Global categories | `politics`, `finance`, `health`, `science_technology`, `environment`, `sports`. The `finance` category includes economy and business reporting. Every provider uses these same IDs. |
| Dates | Start with a shared rolling 90-day window anchored at collection start; expand the shared window to 180 days, then 365 days if needed. Save the actual boundaries. |
| Collection | Real Scrapy spiders for every approved source-language adapter; raw HTML, extraction results, and fetch metadata in MongoDB. |
| Scheduling | Manual repeatable runs now. Airflow is deferred until collection and processing are reliable. |
| Browser rendering | Plain HTTP/Scrapy first; Playwright only when a selected source demonstrably needs JavaScript rendering. |
| Storage | Separate immutable raw content versions, normalized articles, and frozen corpus manifests. Keep MongoDB and Weaviate. |
| NLP compute | Local chunking, embeddings, retrieval, reranking if feasible, and clustering. BGE-M3 stays. |
| Summaries | The legacy Search summary-generation path is superseded by the canonical cited-Q&A path below. |
| Product | A light, readable research workspace with Search, Topics, Corpus, and a dedicated Ask page for independent cited Q&A; see the approved endpoint and workflow in [docs/design.md](design.md). |
| Chatbot goal (grilling) | Answer questions across retrieved articles with a direct synthesis and citations. The selected emphasis is multilingual synthesis, with cross-language interpretation assessed. The bounded readiness review and reporting limits are in [docs/design.md](design.md); no answer quality is established. |
| Chatbot answer language (grilling) | Supported/tested question and answer languages are English, Hindi, Bengali, and Marathi; other languages are outside first-demo tested scope. Answer in the question's language and use available relevant evidence even if it is only in English. There is no minimum number of source languages; demonstrate multilingual synthesis on suitable questions. Translation fidelity requires assessment. No separate language-detector or rejection logic is agreed; mixed-language handling remains unspecified and outside tested scope. |
| Chatbot evidence boundaries (grilling) | Give a supported partial answer, cite what the articles establish, and explicitly identify the unanswered part. When the frozen corpus has no supporting evidence, decline the factual answer, explain that the corpus is insufficient, and do not supplement with model general knowledge. The bounded readiness gate is in [docs/design.md](design.md); no formal scored benchmark or quality threshold is claimed. |
| Chatbot citations (grilling) | Place citations beside factual claims; each citation should expose the original retrieved supporting passage and an article link. This supports inspection but does not itself prove the claim. |
| Chatbot evidence checks (grilling) | Use automatic citation/provenance checks. Agents evaluate RAG during implementation and improve it if needed; the user performs final acceptance, with no intermediate human-label dependency. The first demo has no model-based semantic review at runtime and makes no runtime semantic guarantee. |
| Chatbot conflicting reports (grilling) | Describe disagreements with citations, attribute each account to its source, and do not declare a winner without evidence. The first demo includes no publisher reliability scoring or dedicated automated conflict detector. |
| Chatbot question scope (grilling) | For the first course-demo version, each question stands alone; conversation history and retrieval-query rewriting for follow-ups are out of scope. |
| Chatbot workflow (grilling) | Use a small fixed PocketFlow workflow exposing retrieval, evidence checks, generation, and response checks as stages; reuse existing retrieval and indexing. No dynamic agent. Concrete node stages and validation defaults are approved in [docs/design.md](design.md). |
| Chatbot retrieval (grilling) | Use one existing fixed hybrid retrieval without reranking across corpus languages, using the original question with BGE-M3. Do not make translation calls or multilingual query variants. Assess cross-language misses in testing; make no retrieval-quality claim. |
| Legacy generation paths (grilling) | Remove obsolete legacy chat and unavailable Search summary generation code, contracts, callers, and documentation in favor of one clean cited-Q&A implementation. Preserve reusable retrieval/indexing; update known callers without a compatibility layer for legacy generation paths. The approved endpoint defaults are in [docs/design.md](design.md). |
| Chatbot UI placement (grilling) | Use a dedicated Ask page beside Search, Topics, and Corpus for the independent cited-Q&A purpose. |
| Chatbot response delivery (grilling) | Provide a polished loading and citation experience, then reveal the complete answer only after citation/provenance checks; no answer streaming in the first demo. If OpenAI fails or is unavailable after valid retrieval, show generation unavailable with the retrieved evidence; do not fabricate an answer or switch providers. Timeout, response-validation and error defaults are in [docs/design.md](design.md). Accessible keyboard behavior, reduced-motion support, and truthful status displays are design requirements; no implementation library is chosen. |
| Chatbot model and provider (grilling) | Use `gpt-6-luna` through the direct OpenAI API. Verify account/model access only through an actual application generation test, within the US$0.50 total API cap; do not make standalone access probes. If unavailable, report generation unavailable; do not silently switch model or provider. The user reports holding an API key; its value is not recorded here. |
| Evaluation | BM25, BGE-M3 dense, hybrid; optional measured reranking. BERTopic versus TF-IDF/KMeans. Publish real outputs and limitations. |
| Annotation | Helpers judge search relevance. Publisher sections supply weak topic labels; no manual article-topic labeling requirement or annotation UI. |
| Explicit exclusions | Misinformation/credibility scoring, fake verification badges, general chat, model training, Airflow deployment, automatic language expansion, and an in-app Experiments screen. |

### Acceptance versus aspiration

The collection targets are approximately 2,000 articles, 500 per language, and 250 per adapter. The previously stated 1,000-total, 200-per-language, and 50-per-family-per-language counts are soft planning targets, not acceptance floors. The user explicitly relaxed them after the bounded campaign: retain all four languages and report the qualifying records actually collected, without quota padding or artificial category quotas. Never silently change languages or claim an unachieved target. Report gaps and category counts.

## 2. Initial scout findings (historical; superseded where noted below)

These were findings from the initial pre-implementation audit, not statements
about the current code or data. Dated follow-up verification and slice status
below supersede them. The coordinator writes this plan but does not inspect
application files, implement application changes, or review implementation.

* Initial implementation review found unsupported fallback paths and synthetic evaluation artifacts; Slice 00 below records their removal/disablement and its bounded checks.
* The pre-overhaul ignored datasets were not certified as the curated corpus or valid measurements; they were preserved. The current corpus and result artifacts are identified in the verification report.
* Initial API, identity, URL, hardware and dependency findings above were specific to that audit. Later slice records supersede them; consult current component evidence and the verification report for present behavior.

### Initial pre-plan research-session execution record

The normal-mode scout swarm attempted bounded provider and runtime checks before this plan was finalized. These outcomes are evidence, not completed implementation slices:

| Check | Actual outcome |
| --- | --- |
| ABP Bengali/Marathi HTTP and structured extraction | One full article per language passed direct HTTP with `NewsArticle` body/date fields. No real Scrapy spider run was completed. |
| ABP English/Hindi | Homepages returned HTTP 200 and yielded article links. Follow-up article probes ended without results; bodies remain unverified. |
| Oneindia/Loksatta | Web retrieval exposed the examples below. Local direct requests failed DNS resolution or ended without output. These are not evidence that the publishers block Scrapy. |
| Docker/MongoDB/Weaviate | Docker socket access was denied to the process. A noninteractive sudo attempt was blocked by the execution container's `no new privileges` setting. No containers were started; database health was not verified. No socket permissions, user groups, or existing volumes were changed. |
| GPU | `nvidia-smi` could not communicate with a driver. No genuine CUDA model inference was completed. |
| Lightweight Scrapy/PyMongo test environment | A temporary venv was created at `/tmp/newsintel-check-venv`, outside the repository. Package installation failed resolving `pypi.org`; a later attempt ended without a result. Fixture-spider execution and Mongo integration checks therefore did not run. The scout found no install or Compose process from these checks left running; the temporary venv remains. |
| Application/research changes | At the time of this initial probe, no application files or datasets were changed. |

These entries describe only the initial research-session probes. They are historical and are superseded for Docker, CUDA, and bounded Scrapy/Mongo integration by the dated follow-ups below; they do not describe the current verification status.

### Follow-up runtime verification — 12 November 2026

An independent reviewer reran the infrastructure and model checks after Docker and the configured Python environment became available:

| Check | Follow-up result |
| --- | --- |
| MongoDB and Weaviate | Compose services started and remained running. `make infra-smoke` passed MongoDB read-after-write in the isolated `news_intel_verification` database, removed its temporary record, and received HTTP 200 from Weaviate readiness (version 1.27.3). |
| BGE-M3 embeddings | `python scripts/verify_models.py embedder` passed using the FlagEmbedding backend on the RTX 3050 Ti CUDA device. Two English/Hindi vectors had dimension 1,024 and finite values. |
| BGE reranker | `python scripts/verify_models.py reranker` passed using the CrossEncoder backend on the RTX 3050 Ti CUDA device. Two scores were finite. CUDA fp16 is requested at model load to fit the 4 GB GPU. |
| Reranker regression test | The focused loader test passed for CUDA fp16 and CPU loading behavior. |
| Scrapy to MongoDB | Bounded gate passed on 12 November UTC: all eight selected adapters completed live runs, accepted records and raw references were checked in Mongo, and the independent reviewer passed the lifecycle/quarantine audit. This is a small pilot, not a production reliability or corpus-quality claim; see [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md). |
| Legacy OpenAI summary provider | Not tested during this historical follow-up. This says nothing about the replacement Ask path, whose current status is recorded above. |

The model smokes prove real inference and valid output shapes, not retrieval relevance, ranking quality, answer quality, or Ask provider entitlement. Exact reproducible commands and the independent review are recorded in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).

### Verified implementation gates — 12–13 November 2026 UTC

Slices 02–04 passed their bounded independent gates; Slice 04 was committed as `5325dcf`. The final 90-day campaign contains 516 accepted current articles, 586 raw versions, and 66 rejected raw versions in `news_intel_corpus_v1`. These are the qualifying records actually collected, not a minimum quota or a claim that aspirational targets were met. There are no observed environment-category articles; category labels are section-derived weak labels, and near-duplicate/syndication detection remains deferred. See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for exact commands, counts, preserved pilot attempts, access caveats, and limitations.

### Source roster and validation policy

These eight source-language adapters passed bounded live spider-to-Mongo checks and were used in the final campaign described in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md). A successful technical collection is not publisher permission, production-wide reliability, representativeness, full publisher coverage, or editorial-label accuracy. Keep the campaign counts, source-policy uncertainty, and per-category gaps visible.

| Language | Primary family | Independent second family | Research evidence available before implementation |
| --- | --- | --- | --- |
| English | ABP Live (`abp_en`) | OneIndia English (`oneindia_en`) | Both passed bounded live extraction and Mongo persistence; OneIndia had one expected robots-denied `/partner-content/` candidate. |
| Hindi | ABP News (`abp_hi`) | Amar Ujala (`amarujala_hi`) | Both passed bounded live extraction and Mongo persistence. Amar Ujala's corrected v3 mapping retained six accepted records from health and sports sections. |
| Bengali | ABP Ananda (`abp_bn`) | News18 Bengali (`news18_bn`) | Both passed bounded live extraction and Mongo persistence. The News18 listing selector and pagination were exercised in the bounded run. |
| Marathi | ABP Majha (`abp_mr`) | Loksatta (`loksatta_mr`) | Both passed bounded live extraction and Mongo persistence. Loksatta's configured environment route had no accepted environment article in this pilot. |

OneIndia Marathi is excluded because current research did not establish reliable recent coverage. Do not count sibling editions of ABP as independent families within one language. Record common ownership, syndicated stories, and translations when detectable; multiple URLs are not automatically independent reporting. The pilot's ABP science/technology results included DW-republished reporting, and Loksatta sports had a possible entertainment/editorial false positive; source-section labels remain weak labels pending manual corpus quality sampling.

Example official pages from the research:

* [ABP Bengali sample](https://bengali.abplive.com/news/uttar-pradesh-four-coaches-of-the-chauri-chaura-express-derailed-at-kanpur-central-railway-station-1199028): direct HTTP 200, NewsArticle metadata, publication timestamp, and approximately 2,128 characters of article body.
* [ABP Marathi sample](https://marathi.abplive.com/news/world/pakistan-terrorists-attack-news-major-terrorist-attack-on-a-police-team-in-pakistan-11-police-personnel-killed-on-the-spot-12-others-injured-1445113): direct HTTP 200, NewsArticle metadata, publication timestamp, and approximately 2,196 characters of article body.
* [Oneindia English sample](https://www.oneindia.com/noida/ahead-of-up-elections-2027-centre-clears-rs-2-390-crore-metro-extension-from-noida-sector-51-to-gre-8257019.html) and [Hindi sample](https://hindi.oneindia.com/news/india/union-minister-shivraj-singh-chouhan-mother-kashibai-passes-away-bhopal-aiims-1675049.html): readable publisher content in web retrieval; raw canonical metadata and Scrapy extraction not yet certified.
* [Loksatta sample one](https://www.loksatta.com/mumbai/mumbai-minister-ganesh-naik-pawangad-bungalow-fire-incident-mumbai-print-news-rnb-99-6240560/) and [sample two](https://www.loksatta.com/navimumbai/navi-mumbai-cleanest-city-india-swachh-survekshan-rank-1-6241328/): current Marathi bodies and timestamps visible through web retrieval; not proof that a local spider succeeds.

For failed candidates, the replacement order is: English Indian Express, then Hindustan Times; Hindi Amar Ujala, then Hindustan; Bengali Oneindia Bengali, then Sangbad Pratidin; Marathi Lokmat, then Maharashtra Times. Each replacement must pass the same gate. An access failure, paywall, missing body, or unavailable archive is not a reason to invent data or implement circumvention. Academic use is not blanket permission to retain or redistribute publisher content. The campaign's policy URLs and unresolved access/retention questions are recorded in `artifacts/corpus_campaign/source_access_notes.json`; technical collection does not resolve those questions. Keep raw text local; do not redistribute raw article text or images.

## 3. Architecture and interface decisions

### Collection and corpus identity

Use a small Scrapy package in this repository, integrated with the existing Python configuration. Do not import the unrelated `~/work/digitem/scrapers` project, its credentials, or its 25-field item schema. Reuse its useful practices: per-source selectors, shared validation/storage, bounded retries, and observable run results.

* A source-language adapter has a stable identifier such as `abp_bn`, allowed domains, discovery routes, article selectors/JSON-LD extraction, language expectation, explicit publisher-section-to-global-category mapping, mapping version, and extraction version. Maintain a coverage matrix with one row per approved adapter and columns for all six global categories; each cell records the tested section route and accepted count or an explicit `unknown`/`unavailable` status. A missing route never implies that the category is covered. Common parsing is shared only where live fixtures demonstrate the same structure.
* Crawl one request for each distinct canonical article URL and mapped publisher-section context, bounded by the configured request-pair limit and per-section quota. The stable article ID merges multiple section contexts into one normalized article while preserving each provenance mapping and raw extraction.
* Discover through official RSS, sitemap, category/archive pages, or public APIs. A feed is a discovery mechanism, not a substitute for full article text. Article links must come from the page's primary editorial listing for the mapped section; navigation, sidebar, footer, and generic page-wide anchors are not section evidence. Test selectors against representative category pages and keep regressions for unrelated links. Do not recursively crawl an entire publisher.
* Default to one concurrent request per domain, a two-second delay, AutoThrottle, explicit timeouts, at most two retries for transient failures, bounded page/article limits, and a descriptive user agent. Respect access rules; do not add CAPTCHA, login, or paywall bypass machinery.
* Every run records source IDs, anchored date window, limits, extraction and mapping versions, start/end timestamps, statuses, and discovered/fetched/accepted/rejected/unchanged counts. Failed extraction cannot increment accepted counts.
* Validate canonical publisher URL, nonempty title, substantial body text distinct from the title, supported language, parseable publication timestamp, and absence of obvious menu/login/paywall content. Default minimum body length is 200 Unicode characters; shorter records remain raw but are rejected from this corpus with a reason. Store canonical `categories` and every `category_mappings` provenance entry with the article and raw extraction. Keep unknown/unmapped publisher sections explicitly unknown.
* Use canonical URLs after redirect resolution and removal of known tracking parameters, preserving meaningful path/query components. Derive stable article IDs from publisher identity plus canonical URL, not ingest order. Preserve distinct publishers even for identical text; group exact/near duplicates separately.

MongoDB boundaries:

| Collection | Minimum responsibility |
| --- | --- |
| `crawl_runs` | Run configuration, timing, counters, and errors. |
| `raw_article_versions` | Immutable successful HTML and extracted fields, original/final/canonical URLs, source family/adapter, section context, response status, fetch timestamp, publication timestamp, extractor and mapping versions, and hashes. Unique by article ID, raw HTML hash, extractor version, mapping version, and section context. |
| `articles` | Current accepted normalized article with stable ID, title/body, language, source family/adapter, original URL, dates, canonical global `categories` ID list, all `category_mappings` provenance entries, deterministic primary `category` for compatibility, content hash, and referenced raw version. |
| `corpus_snapshots` | Immutable manifest of exact article/raw versions, content hashes, selection rules, coverage counts, and snapshot ID. |

Identical HTML processed with the same extractor, mapping version, and section context updates run counters and last-seen metadata, without another version document. Changed HTML creates a raw version. An extractor or category-mapping version change creates a new extracted version even when HTML is unchanged. The normalized article's `category_mappings` are the deduplicated union of section contexts observed under the current mapping version, and `categories` is the unique list of their global IDs. Upgrading the mapping version replaces old contexts with those observed under the new version. Only changed normalized article body invalidates embeddings or resets derived state; category remapping alone preserves them. Raw, extraction, mapping, section-context, and embedding version identity must not be conflated. Fetch failures belong to run errors and never overwrite a previous good article. Do not store unbounded fetch history for identical pages.

A snapshot pins the normalized fields used for NLP as well as raw-version references, so later normalization changes cannot mutate an experiment. Store snapshot payloads/manifests locally with checksums and keep their Mongo manifest; do not rely on a mutable `articles` record for replay. Existing data remains untouched until separately backed up and explicitly selected for reuse. Write the new corpus to separate outputs; no default destructive cleanup.

### NLP and index boundaries

* Each chunk retains snapshot ID, stable article ID, version/content hash, chunk number, language, source family, title, publication date, original URL, canonical `categories`, primary `category`, and text. Chunk identity must include article content version and chunk position.
* Use the same snapshot and chunking for comparable retrieval runs. Aggregate ranked chunks into unique articles before judging or displaying article-level results.
* Keep a single active application snapshot at a time. Build a separate index namespace/collection for a new snapshot, verify it, then switch the application configuration. A failed rebuild cannot replace the last working index. Old data is retained until a separate cleanup decision.
* Load models sequentially with small batches. Measure BGE-M3 on this machine before selecting batch sizes or promising latency. Do not hold BGE-M3 and the crossencoder on the 4 GB GPU simultaneously by assumption. CPU execution is an honest fallback, with hardware and latency reported.
* Model loading/inference errors produce unavailable status, never random vectors. BM25 remains an explicit selectable mode when available; it cannot masquerade as dense or hybrid. An optional reranker failure must preserve a clearly identified base ranking and report that reranking did not run.
* Repeated collection changes normalized records, not the frozen evaluation snapshot. Reindex changed versions for a live snapshot only through an explicit rebuild/update command; no implicit mutation of a published experiment.

### API and user experience

Preserve existing search request names (`query`, `lang_filter`, `mode`, `top_k`) and the `results` envelope. Add `published_at` (ISO-8601 timestamp) to each result, retaining existing result field names. Add top-level `metadata` containing `snapshot_id`, `executed_mode` (`bm25`, `dense`, or `hybrid`), `reranker_status` (`disabled`, `applied`, or `unavailable`), and `elapsed_ms`. Return article IDs, genuine URLs, publisher, language, publication date, and excerpts. Ranking scores are labeled as retrieval scores, never credibility or probability. Validation errors use 422; requested unavailable retrieval infrastructure uses 503; a valid search with no matches returns 200 with an empty results array.

Use existing cluster endpoints for Topics with honest empty/error/404 behavior. Return topic terms, size, language/source distributions, representative articles, snapshot ID, and an explicit outlier count. Unknown topic IDs return 404. Call these topics, not detected events.

Add `GET /api/corpus`, returning `snapshot_id`, `article_count`, `language_counts`, `source_counts`, `topic_counts`, `published_from`, `published_to`, `last_successful_crawl_at`, `collection_status`, `rejected_count`, and `duplicate_count`. Scope corpus counts to that snapshot and operational rejection counts to its referenced crawl runs; retain the original timezone in source metadata and normalize API timestamps to UTC. Do not expose raw HTML through this public UI.

The former `POST /api/search/summary` contract and its OpenAI summary configuration are superseded. Replace them and legacy chat with one canonical cited-Q&A implementation using the direct OpenAI API; preserve existing retrieval/indexing. The approved endpoint and API contract are in [docs/design.md](design.md).

The UI uses readable typography, restrained color, real coverage numbers, and accessible keyboard/focus behavior:

* **Search:** query input, language filters, retrieval mode, and article results with real source links and dates. Show loading, no results, and unavailable index explicitly.
* **Ask:** dedicated page for independent cited Q&A; approved interaction and response states are in [docs/design.md](design.md).
* **Topics:** terms, counts and source/language distributions; topic details list real representative articles. Show noise/unassigned coverage rather than hiding it.
* **Corpus:** actual coverage, dates, publishers, latest successful collection, snapshot identity, and important gaps.

Remove obsolete legacy chat and Search summary generation code/contracts/callers, along with unsupported credibility/verification displays. Update known callers to the single canonical cited-Q&A path; no compatibility layer is required for legacy generation paths. No production request may fall back to mock articles. Fixtures are permitted only in tests and visibly separate development previews.

## 4. Experimental design

### Retrieval

Freeze a corpus snapshot, 12 development queries (3/language), and **48 separate held-out test queries (12/language)**. Queries must reflect plausible information needs and include cross-language retrieval, not only copied titles. For each language's test set, include four same-language answer needs, four answer needs supported in another language, and four with useful coverage in multiple languages. Do not tune on test judgments.

Pool the top five unique articles from BM25, dense BGE-M3, and hybrid for each query. Deduplicate per query; the maximum initial test pool is 720 query/article pairs. If the optional reranker is compared, add its top five before freezing that pool, raising the maximum to 960. Helpers judge every pooled candidate as irrelevant (0), partially relevant (1), or directly relevant (2), with readable excerpts and original links. Use bilingual helpers where needed; translation assistance must be disclosed, never treated as native-language validation. Double-judge at least 20% of pairs, report agreement, and adjudicate disagreements. Unjudgeable pairs are excluded with counts, not assigned guessed labels.

Report nDCG@5, MRR@5, and Recall@5 relative to the judged pool, treating grades 1 and 2 as relevant for binary metrics. State that pooled Recall is not exhaustive corpus recall. Report macro averages, per-language and cross-language subsets, query-level outputs, and latency. Queries with no judged relevant article remain visible and are excluded from recall/MRR denominators with explicit counts; do not turn them into successes. Save all ranked IDs, scores, settings, model versions, seeds, snapshot IDs, and hardware. Compare runs on the same judged queries. Do not claim superiority unless measured; negative results are acceptable.

### Clustering

Map publisher sections to the shared global IDs `politics`, `finance`, `health`, `science_technology`, `environment`, and `sports` through a reviewed source-specific table. `finance` includes economy/business reporting. Map the publisher's explicit top-bar or section provenance; do not classify headlines into topics. An article discovered through multiple sections receives a deduplicated canonical `categories` list and `category_mappings` entries shaped `{category, original_category, section_url, mapping_version}`. Merge those mappings onto the same stable article ID while retaining each original section. For compatibility, keep scalar `category` as the deterministic primary global ID using the documented taxonomy order. Category filters and counts use the `categories` list; the scalar is only the primary display/backward-compatibility value. Report the 8-adapter by 6-category coverage matrix, including zero or unavailable cells; do not infer category coverage from an adapter's existence, language, or unrelated sections. Exclude unmapped/multitopic labels only from category-based metrics, while reporting their count and keeping otherwise valid articles searchable. Use the single primary category for NMI/ARI weak-label comparisons; report multi-category membership as coverage counts and do not present ordinary NMI/ARI as multilabel metrics. Use all eligible snapshot articles rather than manufacturing a balanced synthetic topic sample.

Compare BERTopic on real embeddings with TF-IDF/KMeans on the same articles. For the baseline, use character n-gram TF-IDF suitable for the four scripts and six clusters matching the six proxy categories; fix the random seed. Keep BERTopic's actual number of discovered clusters and outliers visible. Report NMI/ARI against publisher-derived categories, overall and per language where defined; report all-document and assigned-document BERTopic results with explicit noise handling. These scores measure agreement with coarse editorial sections, not event truth.

Report language and publisher concentration, duplicate/translation overlap, cluster sizes, representative articles, and outlier rate. Language mixing alone is not a quality metric. Do not require the user to manually label topics or build an annotation interface. Human-readable examples in the report illustrate results and are not an additional gold dataset.

### Q&A and presentation evidence

The main agent only coordinates; subagents execute all tests and review outputs/findings against retrieved evidence. They improve RAG during implementation as needed, then the user performs final acceptance. Project API calls are permitted only inside an actual end-to-end application generation test; no standalone/direct API probes or separate project API judge calls. Total project API spend for implementation testing, including generation and retries, has a hard cap of US$0.50; make no API calls beyond it and stop/report remaining gaps rather than request more budget mid-execution. Subagent review is an engineering check, not genuine human retrieval labels or a runtime semantic guarantee. The bounded readiness gate is in [docs/design.md](design.md); no formal scored benchmark or quality threshold is claimed. Any RAG proxies must be labeled separately from retrieval judgments. This does not change the separate held-out retrieval pool: its 427 query/article pairs still require genuine human judgments, and retrieval quality remains unknown. Do not claim answer quality before it is measured; the course report and slides should contain actual evidence, failures, and what the project does not establish.

## 5. Mandatory execution protocol for every slice

Implementation runs sequentially by slice. Parallelism is allowed only for bounded workers with nonoverlapping file ownership. The coordinator never writes application code, performs project scouting, or reviews code; it assigns tasks, resolves ownership, relays evidence, and tracks gates. The coordinator's only writing exception is this final plan.

Each slice must use the following ordered phases; the slice descriptions below specialize their assignments and acceptance evidence. Verification is risk-targeted: run the smallest existing focused checks that cover changed behavior and required acceptance gates. Do not add broad or duplicate test suites without a specific uncovered risk; record any skipped gate and its reason.

1. **Scout phase:** named read-only scout(s) inspect current code, callers, tests, configuration, dependencies, and applicable AGENTS/skills. Return exact file/line references, current interfaces, risks, a bounded file-ownership proposal, and the checks needed. Use Context7 CLI for current library/framework/API usage as required by AGENTS. Do not ask the user for discoverable facts.
2. **Worker phase:** coordinator passes the scout packet and acceptance criteria to bounded worker(s). Each has an explicit allowlist of files/subsystems, inputs, outputs, and tests. Shared files have one owner; cross-owner requests return to the coordinator. Workers implement the whole authorized slice including affected callers and focused regression checks.
3. **Independent review phase:** a reviewer who did not implement that work inspects the connected behavior and runs the actual relevant checks. Return **PASS** or **NEEDS_FIX**, with severity, file/line evidence, and reproducible failures. Skipped checks and environmental blockers are explicit. A blocker is not PASS.
4. **Fix loop:** for NEEDS_FIX, assign bounded fixer(s) owning the identified problem. Re-run focused checks and send the result to the independent reviewer. Repeat until PASS; no arbitrary iteration cap that permits an incomplete slice to pass.
5. **Documentation phase:** only after code PASS, a docs agent updates all affected setup/API/architecture/data/experiment/presentation instructions and examples. Remove superseded claims rather than adding contradictory prose. New docs exist only where needed.
6. **Documentation verification:** reviewer checks docs against actual commands, interfaces, and measured results. If docs expose a code gap, reopen the fix/review loop, then refresh docs. Require code and docs PASS together.
7. **Commit phase:** a separate commit agent checks status/diff, includes only that slice's approved files, excludes secrets/raw corpora/generated bulky artifacts/unrelated user work, and creates the specified commit. Return commit hash and clean/remaining status. Coordinator advances only then.

Every handoff records slice ID, owner, owned files, dependencies, decisions, test evidence, open blockers, docs changes, and commit hash. Never use fake service/model output to satisfy a gate. If blocked, do independent work within the same slice and record the blocker; do not falsely mark the slice complete. User authorization covers these per-slice commits, not remote publishing or destructive data cleanup.

## 6. Phases and implementation slices

Time allocations total approximately 12 working days, leaving two days of integration/failure buffer. They assume two or more bounded workers where ownership allows, plus language-capable helpers for judgments; they are not a one-person effort estimate or permission to skip acceptance. Four languages and all eight approved adapters remain requirements. Article-count targets are aspirations; report the actual qualifying corpus without padding. Reranking, browser-rendered sources, and working summaries are stretch outcomes; the minimum honest presentation uses BM25/dense/hybrid, real topics, and the three core screens.

Apply these stop rules without another user questionnaire: spend at most half a day attempting GPU setup, then run genuine BGE-M3 on CPU and report timing; time-box source probes and replace failed publishers rather than engineering bypasses; collect a bounded valid corpus and report actual counts, without treating former numeric floors as gates; omit optional reranking, browser rendering, and summaries before cutting provenance or evaluation honesty. If eight approved adapters or real model inference still cannot pass their early gates, mark the schedule blocked and report the exact constraint rather than reducing agreed requirements silently. Use the final buffer for integration, not new features.

The saved held-out run produced 427 unique query/article pairs from 720 possible top-five slots across the three systems; development rankings were run separately and are not part of the judging pool. At least 86 pairs (ceil of 20%) must be double-judged, for at least 513 initial helper decisions before adjudication. Split assignments across language-capable helpers. If helper coverage is unavailable, retain the blinded pool and mark retrieval evaluation incomplete rather than substitute generated judgments. Slice 07 produces clustering measurements once; Slice 09 incorporates those saved results into the combined report without repeating topic annotation or metric work.

### Phase A — Make the foundation truthful and runnable

#### Slice 00 — Remove fabricated success and protect existing data (~0.5 day) — COMPLETE (commit `0e23cfa`)

* **Scouts:** one API/core scout maps every fake article/model/credibility/evaluation fallback and its callers; one UI/docs scout maps frontend mocks and unsupported claims. Inventory ignored local data without deleting it.
* **Workers:** backend worker owns API/core fallbacks and truthful statuses; frontend worker owns API-client mock catches and unsupported badges; one worker owns any shared contract changes. Disable misleading experiment paths until replaced, retaining only explicit test fixtures.
* **Review/fix:** independent reviewer checks unavailable service/model, empty search, unknown topic, and absent API key cases; failure must never produce attributed synthetic news, random embeddings, or gold-derived scores. Fixers follow the mandatory loop.
* **Docs:** docs agent removes misleading metrics, fake verification claims, misinformation scope, and stale no-scraping claims; records current honest limitations and preservation policy. Reviewer verifies the wording.
* **Commit:** commit agent creates `fix: remove fabricated news and evaluation fallbacks` only after both gates pass.

**Completion evidence:** Independent frontend review passed 15 focused Node checks, lint, production build and production dependency audit (0 findings); development dependencies still have 7 moderate audit findings. Independent backend/retrieval and evaluation-safety reviews passed their focused checks and compile/diff checks. Manual readiness stubs confirmed degraded status for unavailable embedding/index dependencies and ready status when configured dependencies were usable. These checks do not establish a populated index, retrieval quality, provider access or end-to-end UI acceptance. The existing ignored datasets and result artifacts remain untouched; the legacy loader refuses the configured application database, and legacy generated evaluation entrypoints are disabled. No paid provider or corpus write was used for these gates. Slice 00 was committed as `0e23cfa`.

#### Slice 01 — Reproducible local runtime and hardware gate (~0.5 day) — COMPLETE

* **Scouts:** runtime scout checks actual Python environment/lock conventions, Docker endpoints and existing volumes, model configuration, GPU access, frontend scripts, and applicable setup instructions. No destructive reset or system permission changes.
* **Workers:** runtime worker owns reproducible Python/Scrapy dependencies and Makefile/configuration; infra worker owns existing Compose health checks and local service configuration, with no overlap. Preserve database volumes, avoid public unauthenticated exposure, and keep secrets in local environment files.
* **Review/fix:** reviewer starts/checks MongoDB and Weaviate where permitted, runs database health checks, then a tiny real BGE-M3 inference and index write/read in a dedicated test namespace. Measure CPU/CUDA memory and a small batch latency. Check frontend build scripts. Missing Docker/CUDA is recorded as a blocker or explicit CPU path, never hidden.
* **Docs:** docs agent writes the exact tested setup/start/health commands, dependency installation, CPU setting, GPU prerequisites, resource budget, and recovery steps; reviewer verifies them on this environment as far as access permits.
* **Commit:** `build: make local NLP and database setup reproducible`.

**Current status:** Complete; code, setup/report documentation, and independent verification are committed as `1151058`. A 154-package CPU lock install/import gate, MongoDB read/write, isolated Weaviate vector write/read/delete, real local CUDA embedding/reranker inference, and API readiness/health startup passed independent review. The active CUDA environment was preserved; CPU inference was not run. These checks do not validate retrieval quality or release readiness. See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for exact environments and results.

### Phase B — Acquire a traceable four-language news corpus

#### Slice 02 — Certify the eight source-language adapters (~1 day)

* **Scouts:** split discovery by language pairs: EN/HI and BN/MR. Inspect official feeds/sitemaps/categories, actual article HTML, publisher access notes, date coverage, language, source ownership, and section-to-topic possibilities. Probe the selected roster before replacements.
* **Workers:** two source workers own nonoverlapping source probe/fixture files and source-registry entries; each creates bounded actual Scrapy smoke probes, not only requests/browser screenshots. A single registry owner integrates shared metadata. Avoid adding Playwright unless a source needs it and its rendered extraction is tested.
* **Review/fix:** reviewer requires at least three distinct live article successes per adapter spanning two sections when available, plus ten candidate-URL checks for discovery/date/body acceptance. Retain representative permitted/sanitized fixtures and prove parser failure is explicit. A one-page HTTP 200 is insufficient. Record accepted/rejected/error counts, selectors, raw/structured fields, and recent/archive access. Replace failures in the stated order; repeat the gate for replacements.
* **Docs:** create a concise source register with approved adapters, exact official URLs, discovery routes, tested dates, extraction strategy, coverage/access limitations, publisher family, and topic mappings. Reviewer checks that candidates are not labeled approved.
* **Commit:** `test: validate multilingual news source adapters`.

#### Slice 03 — Shared Scrapy pipeline and Mongo version storage (~1 day)

* **Scouts:** persistence scout maps existing normalization/dedup callers and Mongo integration; collector scout maps approved source outputs and required lifecycle hooks. Return the smallest common item and storage contract.
* **Workers:** collector worker owns Scrapy settings, shared item validation and run lifecycle; storage worker owns Mongo indexes, stable identity, version persistence and normalization integration. One worker owns the integration boundary and runs its end-to-end test; no shared-file parallel edits.
* **Review/fix:** reviewer tests initial fetch, identical re-fetch, changed HTML, changed normalized body, extractor-version change, redirects/tracking URLs, transient failures, malformed records, and restart/idempotence against real MongoDB in a test database. Previous accepted content must survive errors. Confirm raw HTML and provenance are actually stored and secrets are excluded.
* **Docs:** docs agent updates architecture/setup with raw/current/snapshot boundaries, indexes, version rules, retention, manual run commands, and retry/error semantics; reviewer checks them.
* **Commit:** `feat: persist versioned Scrapy articles and crawl runs`.

#### Slice 04 — Complete spiders and collect the curated corpus (~1.5 days)

* **Scouts:** per-family scouts reconfirm approved extraction fixtures, date pagination, selectors, and source section mappings against the shared pipeline. Identify shared parsing only where proven.
* **Workers:** bounded source workers own disjoint spider files/fixtures; a single integration worker owns registry and collection command wiring. Implement every approved adapter with date/limit controls and the common storage path. Run bounded pilots first, then the anchored corpus collection; no scheduler deployment.
* **Review/fix:** reviewer executes each spider through Scrapy and verifies stored raw HTML, complete accepted fields, stable IDs, dates/language/topic mappings, rate limits, and replay/idempotence. Compare counters to Mongo records. Examine sampled accepted pages for menu/paywall/non-news contamination. Expand the shared date window only by the documented rule; apply duplicate grouping without erasing source provenance.
* **Docs:** docs agent updates source register, runbook, actual coverage and rejection reasons, window expansion, known gaps, and rerun commands. Reviewer verifies counts against the collected data.
* **Commit:** `feat: collect four-language news with approved Scrapy spiders`. Commit code and manifests only, not full copyrighted HTML or bulky corpus exports.

**Current status:** Collection and independent read-only audit passed for campaign `corpus-20261112T194939Z` in isolated database `news_intel_corpus_v1`: 516 accepted current articles, 586 raw versions, 66 rejected raw versions. Slice 04 was committed as `5325dcf`. The former numeric floors were relaxed to soft targets; the actual corpus is reported without padding. See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for adapter/category counts, reproduction commands, attempt history, access caveats, and quality limits.

### Phase C — Freeze data and deliver honest NLP behavior

#### Slice 05 — Frozen corpus, chunks, and provenance-preserving index (~1 day)

* **Scouts:** data scout traces current IDs, normalization/chunk boundaries, Parquet/vector alignment and language assumptions; index scout traces Weaviate properties, deletion/rebuild behavior, URL loss, and retrieval metadata callers.
* **Workers:** data worker owns corpus selection, deterministic snapshots, versioned chunks and manifests; index worker owns indexing/schema and active snapshot switching. One owner controls shared configuration. Preserve old artifacts separately; never assume they align with the new snapshot.
* **Review/fix:** reviewer rebuilds a small snapshot twice and checks stable IDs/checksums, chunk/vector cardinality and order, original URLs through index readback, repeated-story handling, source/language counts, and crash-before-switch behavior. Changing a live article must not alter a frozen snapshot. Confirm no fake/review/poem/title-only records enter the new corpus.
* **Docs:** docs agent updates data dictionary, snapshot/rebuild/recovery commands, provenance path and actual corpus statistics; reviewer reproduces the small replay.
* **Commit:** `feat: freeze reproducible corpus snapshots and indexed provenance`.

**Current status:** Complete; code, independent verification, documentation, and commit `4b218ea298226d7ba4008da27d1124274468d40e` passed. Snapshot `corpus-59b2b589fe3bbdbffdc3` freezes 516 articles and 2,135 chunks in `data/snapshots/<snapshot-id>/` with manifest SHA-256 `0c56de1aafcbd32d19e68f8c0b99f2f31f1f5c5e89a49cbeae20acf416bb5eb2` and chunks SHA-256 `db3f0a1727b264f5c73df330e407ea3468f34c812d3b36d94b76e3fd7b303c16`. Counts by language are English 123, Hindi 116, Bengali 156, Marathi 121. Its dedicated Weaviate collection is `NewsChunkSnapshotdcc85b7d4a2e9122136846f3874bca65af0ce6d0`; all 2,135 stored IDs, provenance fields and vectors matched the cached embeddings on paged readback. The active config points to this snapshot, collection and `news_intel_corpus_v1`; legacy databases and artifacts were retained. The first activation preceded the later vector-readback requirement; a corrected cache-reuse build completed full readback before reactivating. Exact commands and gate scope are in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) and [setup.md](setup.md).

#### Slice 06 — Search, evidence summaries, and corpus API (~1 day)

* **Scouts:** API scout traces search/retrieval/reranker/summary callers and response types; contract scout maps frontend consumers and health semantics. Confirm actual OpenAI SDK/API syntax with current official documentation and account access with a bounded smoke call when credentials exist.
* **Workers:** retrieval worker owns ranked unique-article retrieval, explicit executed mode and optional reranker status; API worker owns response metadata, corpus endpoint, evidence-bound summaries and error contracts. Coordinate shared types through a single owner. No frontend redesign in this slice.
* **Review/fix:** reviewer tests all three retrieval modes, all four language filters, chunk-to-article aggregation, source URLs, snapshot mismatch, absent models/index, reranker failure, and unavailable OpenAI. Verify summary citations belong to actual retrieved evidence and that search succeeds when generation fails. Measure local latency without promising a target beforehand.
* **Docs:** docs agent updates API reference/examples, configuration and failure states, model/hardware notes, and summary cost/access limitations; reviewer validates examples against actual responses.
* **Commit:** `feat: expose honest multilingual search and corpus evidence`.

**Current status:** Complete; code, independent review, documentation review and commit `c29f1639f56323de8b6c45fc46ba84711dc71b07` passed. The search API exposes ranked unique articles with actual mode/snapshot/reranker metadata; `/api/corpus` reports verified snapshot facts and marks unavailable crawl/rejection metadata; `/api/search/summary` validates supplied evidence but generation remains unavailable pending verified provider access. Focused gates and API smoke results are recorded in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).

#### Slice 07 — Topics and real clustering baseline (~1 day)

* **Scouts:** clustering scout maps BERTopic persistence, topic IDs, outlier handling and cluster API callers; evaluation scout maps synthetic cluster evaluation and publisher-section coverage. Return the fixed comparison protocol.
* **Workers:** topic worker owns real snapshot clustering, persisted topic metadata and empty/404 behavior; baseline worker owns TF-IDF/KMeans evaluation, section mapping validation, metrics and saved artifacts. One owner manages shared topic/category configuration.
* **Review/fix:** reviewer runs both methods on the same frozen snapshot, verifies article membership and snapshot IDs, checks unmapped labels/outlier denominators, reproduces seeded baseline output, and checks empty-run/unknown-topic errors. NMI/ARI must come from actual labels/predictions, not fabricated arrays. Inspect publisher/language concentration and duplicate overlap.
* **Docs:** docs agent documents topic-versus-event terminology, category proxies, noise policy, methods and measured limitations; reviewer checks artifact-to-report consistency.
* **Commit:** `feat: add reproducible topic exploration and clustering baselines`.

**Current status:** Complete; code, documentation, and independent review are committed as `e407f82`. The real run used all 516 articles from `corpus-59b2b589fe3bbdbffdc3`, reused verified cached chunk embeddings, and ran BERTopic on CPU. The saved comparison uses a repeatable six-cluster character-TF-IDF/KMeans baseline and publisher-section weak labels. It found 11 non-noise topics, 17 outliers, and records all-document/assigned-only and per-language metrics; these are not factual-truth or event-coherence scores. The snapshot-scoped API reads verified local artifacts and exposes topic counts, provenance, detail pagination, and empty/404/503 behavior. Exact commands, artifact IDs, checksums, measured results and limitations are in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) and [setup.md](setup.md). The focused code/API gates passed; no broad suite or algorithm rerun was performed for this documentation update.

### Phase D — Present and substantiate the project

#### Slice 08 — Search, Topics, Corpus research workspace (~1.5 days)

* **Scouts:** UI scout maps routes, components, theme, API clients, types, responsiveness and local Next.js instructions; accessibility scout identifies keyboard/focus/contrast and loading/error requirements. Before Next.js code, workers read the required installed Next documentation and fetch current library docs per AGENTS.
* **Workers:** shell/design worker owns global layout/navigation/theme and shared primitives; search worker owns Search/results/summary; explorer worker owns Topics/Corpus. Shared types/API client have a single assigned owner. Remove obsolete Chat navigation/page and credibility displays after callers are mapped.
* **Review/fix:** independent UI reviewer checks narrow and wide layouts, keyboard use, accessible labels/focus, real links/dates/counts, long Indic text, and every documented loading/empty/error/unavailable state. Run actual frontend lint/build commands supported by this repo; use bounded browser smoke checks. Network/model failure must not display mock articles or verification claims.
* **Docs:** docs agent updates frontend/setup/product guide and captures actual-data screenshots with limitations where needed; reviewer checks screenshots and navigation match the implementation.
* **Commit:** `feat: present Search Topics and Corpus as a research workspace`.

**Current status:** Implementation, independent UI review, and documentation are complete; committed as `8063962`. Independent checks passed frontend client tests (14/14), lint, production build, and browser checks against the active snapshot at desktop and 390px mobile widths. The UI displays real Search/Topics/Corpus data and explicitly handles simulated empty/error/stale states. These checks do not evaluate retrieval relevance, summary quality, or topic usefulness. Evidence and limits are recorded in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) and [frontend_guide.md](frontend_guide.md); screenshots from the final clean browser build are in [docs/images/slice08](images/slice08/).

#### Slice 09 — Held-out retrieval experiments and honest results (~2 days)

* **Scouts:** evaluation scout maps current leakage/simulation paths, retrieval interfaces, snapshot artifacts and available language-capable helpers; report scout maps metric claims across README/slides/docs. Collect helper judgments only on the frozen pool with the stated rubric.
* **Workers:** evaluation worker owns real baseline runners, query/judgment formats, pooling and metrics; analysis worker owns saved run summaries and charts from actual artifacts, without changing metric implementations. The shared frozen query/judgment files have one owner and a recorded freeze checksum.
* **Review/fix:** reviewer verifies disjoint dev/test queries, no gold IDs in retrieval, all pool judgments and disagreement handling, identical snapshot inputs, unique article ranking, metric hand calculations on a small fixture, and reproducibility of one saved run. Reranker comparison is omitted if it cannot run honestly or cannot be judged in the same pool. Report zero/poor results as measured.
* **Docs:** docs agent produces the experiment report with real corpus counts, baselines, per-language/cross-language metrics, clustering comparison, latency/hardware, examples, confidence limits and failure cases; removes all stale simulated metrics. Reviewer traces every headline number to a saved run.
* **Commit:** `eval: publish measured multilingual retrieval and topic results`.

**Current status:** Retrieval evaluation engineering is committed as `a595c4d`, but relevance-quality acceptance remains unmet pending genuine helper judgments. The frozen, corpus-derived query set has 12 dev and 48 held-out queries (15 per language across English, Hindi, Bengali and Marathi); the held-out set has four same-language, four cross-language and four multilingual needs per language. BM25, BGE-M3 dense, and hybrid each ran once on all 48 held-out queries. A separate 12-query dev run used unchanged settings; no held-out tuning occurred. The query set is not representative of reader needs. The held-out rankings pool to 427 distinct query/article pairs; the blinded local helper packet contains short excerpts, not full-text exports. The score remains `incomplete` with null metrics because no human labels exist. No retrieval-quality claim is allowed yet. Independent evaluation engineering/provenance checks passed (eight focused checks); relevance quality was not met. Reranking was omitted before pool freeze. The protocol, exact commands, saved artifact checksums, retrieval-only latency, rubric, JSONL schema, required 86 double-judged pairs, and helper handoff are in [retrieval_evaluation.md](retrieval_evaluation.md); the measured run record is in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md). Slice 09 must not be marked fully complete until real judgments, agreement/adjudication, and score review are complete.

#### Slice 10 — Faculty demonstration, documentation audit, and release rehearsal (~1 day + buffer)

* **Scouts:** release scout checks setup/demo reproducibility and all stale feature/stack/metric claims; presentation scout maps the project rubric to demonstrable evidence. Inspect changes since the previous review rather than repeating the entire audit.
* **Workers:** release worker owns narrow integration fixes and demo commands; presentation worker owns report/slide/demo-script source files. Fixes stay bounded; no feature expansion. Keep a real frozen local snapshot for reliable demonstration, not invented offline data.
* **Review/fix:** independent reviewer runs the supported setup path and rehearses Search → cross-language results → original source → Topics → Corpus → measured experiment table, followed by Ask only after bounded app tests and passage review are complete. Test live Ask states and real snapshot recovery. Confirm no secrets/bulky raw corpus are staged, all referenced metrics are real, and required checks passed. Record remaining environmental blockers rather than declaring release-ready.
* **Docs:** docs agent reconciles README, setup, architecture, API reference, project purpose/problem statement, frontend guide, presentation guide and existing slide context. State exactly what is complete, limited, optional, or deferred. Reviewer verifies docs against the rehearsal.
* **Commit:** `docs: prepare reproducible NLP course demonstration` only after integration and docs PASS. No remote deployment or publishing is implied.

**Current status:** The bounded local runtime rehearsal passed on 13 November 2026; independent documentation review passed, with commit pending. It verified the configured API/UI path, Search → cross-language results → original source → Topics → Corpus → retrieval latency table, and the unavailable summary state. The source returned HTTP 200 during the rehearsal. Playwright's 503 screen was explicitly simulated by interception; no service was stopped. Cached-vector recovery restored 2,135 chunks to a scratch Weaviate in 6.012 seconds with `activate=False`, no re-embedding, and successful BM25/nearest-vector provenance queries. Original MongoDB, Weaviate, configuration and snapshot hashes remained unchanged; temporary services and listeners were cleaned up. Evidence is `artifacts/demo_rehearsal/runtime_rehearsal.json`. This verifies the current configured local environment only: fresh-clone reinstall/full-pipeline was not tested. CPU dependency-lock install/import was verified separately; CPU model inference was not.

The handoff uses eight adapters: `abp_en`, `oneindia_en`, `abp_hi`, `amarujala_hi`, `abp_bn`, `news18_bn`, `abp_mr`, `loksatta_mr`. The final campaign has 516 accepted articles, 586 raw versions, 66 rejected versions; the active snapshot has 516 articles and 2,135 chunks across four languages and five publisher families. Snapshot `corpus-59b2b589fe3bbdbffdc3` manifest SHA-256 is `0c56de1aafcbd32d19e68f8c0b99f2f31f1f5c5e89a49cbeae20acf416bb5eb2`; chunks SHA-256 is `db3f0a1727b264f5c73df330e407ea3468f34c812d3b36d94b76e3fd7b303c16`. BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181` ran on RTX 3050 Ti Laptop GPU/CUDA fp16 for the held-out baseline. Retrieval run is `artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json`; topic run is `bertopic-20261112T205209237980Z-177ffa64`. The 48-query retrieval pool has 427 pairs and remains unjudged (`metrics: null`); at least 86 pairs require double judgment and the full initial workload is at least 513 decisions, followed by agreement, adjudication and score review. The real BM25/dense/hybrid latency table and exact commands are recorded in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) and [setup.md](setup.md). Optional/deferred work: relevance annotation; source/category quality sampling; near-duplicate/syndication checks; Ask final user acceptance (tracked in [docs/design.md](design.md)); Airflow/continuous collection; fresh-clone full-pipeline rehearsal. Overall completion is not claimed.

## 7. Completion checklist and handoff

The overhaul is complete only when approved spiders exist for the actual eight adapters, Mongo raw/version storage is demonstrated, a frozen real corpus is indexed with source URLs, Search/Topics/Corpus work without fabricated fallbacks, and the held-out baseline report can be reproduced. The report must include weak-label and pooled-relevance limitations. A polished screen alone is not completion.

At every slice end, the coordinator reports the independent verdict, focused checks, docs changed, commit hash, and unresolved constraints. The final handoff includes the approved source register, corpus snapshot ID/checksum, real counts, model/hardware configuration, experiment run IDs, exact demo commands, and the optional/deferred work list.

Deferred: Airflow DAGs, continuous ingestion, model training, extra languages, misinformation detection, production hosting, broad scraping infrastructure, and annotation-product features. When Airflow is eventually added, call the already tested collection/normalization/snapshot commands; do not move article payloads through scheduler task messages or create a second extraction path.

Research limitations: the initial audit did not prove full-corpus cleanliness, the eight bounded extractors, CUDA inference, OpenAI account access, or end-to-end service health. Later follow-ups passed local infrastructure, real CUDA inference, the bounded eight-adapter Scrapy/Mongo gate, frozen snapshot/index verification, topic artifact checks, search API checks, and Slice 08 UI acceptance. The bounded Slice 10 runtime rehearsal passed in the configured local environment; a fresh-clone/full-pipeline rehearsal remains untested. Held-out human-judged retrieval evaluation and Ask user acceptance remain outstanding. The GPU was verified with fp16 on 4 GB VRAM; this is an execution result, not a quality or throughput evaluation.
