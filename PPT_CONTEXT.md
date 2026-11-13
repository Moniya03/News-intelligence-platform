# Faculty presentation context

This is source material for preparing a presentation, not a generated slide
deck. Use [the presentation guide](docs/presentation_guide.md) for the demo
runbook and [the verification report](docs/VERIFICATION_REPORT.md) for the
evidence register.

## Project

**Title:** Multilingual News Retrieval and Topic Exploration

**Question:** Can multilingual embeddings help retrieve Indian news across
English, Hindi, Bengali and Marathi, and can topic clustering help readers
browse a collected corpus?

**Scope:** Eight source-language Scrapy adapters; MongoDB raw/current article
records; frozen snapshot `corpus-59b2b589fe3bbdbffdc3`; 516 accepted articles,
586 raw versions, 66 rejected versions and 2,135 chunks. Search offers BM25,
BGE-M3 dense and hybrid retrieval. Topics uses a saved BERTopic run.

**Verified runtime:** Search, Topics and Corpus were rehearsed locally. A
cross-language query produced results in all three UI modes, and the original
source returned HTTP 200 during rehearsal. Topic output has 11 non-noise topics
and 17 outliers. Cached-vector recovery restored all 2,135 vectors into an
isolated scratch index in 6.012 seconds with activation disabled and no
re-embedding. The original MongoDB, Weaviate, config and snapshot hashes were
unchanged after the rehearsal.

## Evidence and limits

- The held-out baseline has 48 queries and 427 distinct pooled
  query/article pairs. Retrieval-only mean latencies: BM25 30.62 ms, dense
  79.41 ms, hybrid 85.72 ms. Dense/hybrid include query embedding time.
- Its score is `incomplete` with `metrics: null`: no human relevance labels
  exist. Do not claim that any retrieval mode is better. Reranking was omitted
  from the saved evaluation pool; the UI smoke did exercise its configured
  reranker.
- Corpus language counts are English 123, Hindi 116, Bengali 156, Marathi
  121. There are five publisher families. Categories are weak publisher
  section labels, environment count is zero, and source concentration plus
  near-duplicate/syndication checks remain concerns.
- Topic comparison against publisher-section labels measures weak-label
  agreement, not truth or event coherence.
- Summary provider access is unverified. The displayed summary state says
  unavailable. The Playwright HTTP 503 state was explicitly simulated by
  request interception; no service was stopped.
- A fresh CPU dependency-lock install/import gate passed separately. No fresh
  clone, CPU model inference, or complete fresh-clone collection-to-demo
  pipeline was tested.

## Do not include

Do not use claims or results about fake-news detection, credibility/veracity,
consensus, Tamil, 54,102 chunks, fabricated fallback content, synthetic
retrieval/RAG metrics, perfect accuracy, representative coverage, or overall
project completion. The earlier material containing those claims has been
removed from this presentation context.

## Reproducibility identifiers

- Snapshot manifest SHA-256:
  `0c56de1aafcbd32d19e68f8c0b99f2f31f1f5c5e89a49cbeae20acf416bb5eb2`
- Snapshot chunks SHA-256:
  `db3f0a1727b264f5c73df330e407ea3468f34c812d3b36d94b76e3fd7b303c16`
- Topic run: `bertopic-20261112T205209237980Z-177ffa64`
- Retrieval run: `artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json`
- Pooled score: `artifacts/retrieval_eval/v1/scores/corpus-59b2b589fe3bbdbffdc3/scores.json`
- Rehearsal record: `artifacts/demo_rehearsal/runtime_rehearsal.json`

## Deferred

Human relevance annotation and score review; source/category quality sampling;
near-duplicate and syndication detection; provider access verification;
Airflow and continuous collection; fresh-clone full-pipeline rehearsal.
