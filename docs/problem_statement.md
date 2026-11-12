# Problem statement

## Motivation

Readers who search in one language may miss reporting published in another. This project investigates a specific information-retrieval question: can multilingual representations retrieve relevant Indian news across English, Hindi, Bengali and Marathi, and can topic clustering help people browse the resulting corpus?

This is a research hypothesis, not an established result. Lexical retrieval may work well for same-language queries and named entities; multilingual dense retrieval may help with cross-language queries. Both possibilities require a suitable corpus and a relevance-labeled evaluation before conclusions can be drawn.

## Research objectives

1. Build a small, documented collection of real news articles with publisher, source URL, language, date, category provenance and raw-record lineage.
2. Compare BM25, dense and hybrid retrieval on the same frozen corpus and judged queries.
3. Explore whether clustering provides a useful browsing aid, and report its limitations.
4. Present failures, coverage gaps and uncertainty alongside any measured results.

## Non-goals

The project does not determine whether an article is true, score publisher credibility, detect misinformation, or guarantee that generated answers are correct. Any answer feature must cite retrieved evidence and be evaluated separately.

## Evidence status

Eight selected source-language adapters passed a bounded live crawl and Mongo persistence review. Local embedding and reranker inference also ran successfully. The pilot is small and category coverage is uneven; no retrieval-quality or clustering-quality claim follows from these checks. See [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for evidence and [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md) for acceptance criteria and remaining phases.
