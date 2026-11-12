# Faculty presentation guide

## Present the project honestly

**Working title:** Multilingual News Retrieval and Topic Exploration

**Research question:** Can multilingual embeddings help retrieve Indian news across English, Hindi, Bengali and Marathi, and can topic clustering help readers browse a collected corpus?

Describe this as an NLP project in progress. The bounded scraper pilot and local model inference are verified engineering results. They do not prove that retrieval is relevant, the corpus is representative, or clusters are useful. The old misinformation, credibility, accuracy and clustering metrics were synthetic or otherwise invalidated; do not show them as results.

## Suggested 8–10 minute structure

1. **Motivation (1–2 min):** Readers can miss reporting published in another language. Frame this as a question to test, not an assumed benefit.
2. **Method (2 min):** Explain collection with provenance, a frozen corpus, and BM25/dense/hybrid retrieval comparison. Describe topic clustering as a planned exploration.
3. **Evidence so far (2 min):** Show the bounded eight-adapter Scrapy-to-Mongo pilot and verified local BGE-M3/reranker execution. State sample size and coverage limits from [the verification report](VERIFICATION_REPORT.md).
4. **Limitations and next work (2 min):** The pilot is not a research corpus; retrieval and clustering quality have not been evaluated on a judged, frozen dataset. Explain the remaining roadmap slices.
5. **Demo or discussion (1–2 min):** Demonstrate only a path that you have checked against the current local data and services. If the corpus/index is unavailable, show API behavior or screenshots clearly labeled as implementation views, not successful research results.

## Claims to avoid

Do not claim fact-checking, credibility scoring, zero hallucinations, cross-source consensus, proven cross-lingual retrieval quality, complete four-language coverage, a representative corpus, or any unverified numeric score. The app cannot determine whether a story is true. A successful model smoke test checks execution and output shape only.

## Before presenting

- Read [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for what was actually measured.
- Read the current status and acceptance criteria in [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md).
- Verify the exact UI flow and indexed data on the machine used for the talk. Do not assume local development server availability means the research pipeline works.
- Clearly label the pilot as a pilot and discuss uneven source/category coverage.
