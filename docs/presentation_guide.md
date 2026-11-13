# Faculty presentation guide

## Present the project honestly

**Working title:** Multilingual News Retrieval and Topic Exploration

**Research question:** Can multilingual embeddings help retrieve Indian news across English, Hindi, Bengali and Marathi, and can topic clustering help readers browse a collected corpus?

Describe this as an NLP project in progress. The active local snapshot has 516 accepted articles, 586 raw versions and 66 rejected raw versions; it contains 2,135 indexed chunks. The bounded runtime rehearsal verified the interface and recovery path, not retrieval relevance. The corpus is not representative, and the saved held-out retrieval score has null metrics because it has no human judgments. The old misinformation, credibility, fake-news and unsupported retrieval metrics were synthetic or otherwise invalidated; do not present them as results.

## Suggested 8–10 minute structure

1. **Motivation (1–2 min):** Readers can miss reporting published in another language. Frame this as a question to test, not an assumed benefit.
2. **Method (2 min):** Explain the eight Scrapy adapters, provenance, frozen snapshot, and BM25/dense/hybrid comparison. Describe topic clusters as exploratory groupings.
3. **Evidence so far (2 min):** Show the verified corpus counts, snapshot/index hashes, 48 held-out query rankings and real retrieval-only latency table. Make clear that latency is measured, relevance quality is not. State source/category limits from [the verification report](VERIFICATION_REPORT.md).
4. **Limitations and next work (2 min):** Explain that 427 pooled pairs still need human labels, including at least 86 double judgments and at least 513 initial helper decisions. Topic comparison uses weak publisher-section labels. Near-duplicate/syndication checks and source representativeness are unresolved.
5. **Demo (1–2 min):** Use the runbook below for Search → cross-language result → publisher source → Topics → Corpus → latency table, then show one of the reviewed Ask examples if the services are available. The original source returned HTTP 200 during rehearsal. If showing the historical error screen, identify the Playwright 503 as simulated; no live service was stopped.

## Claims to avoid

Do not claim fact-checking, credibility scoring, zero hallucinations, cross-source consensus, proven cross-lingual retrieval quality, complete four-language coverage, a representative corpus, or any unverified numeric score. The app cannot determine whether a story is true. A successful model smoke test checks execution and output shape only.

## Before presenting

- Read [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md) for what was actually measured.
- Read the current status and acceptance criteria in [OVERHAUL_PLAN.md](OVERHAUL_PLAN.md).
- Verify the exact UI flow and indexed data on the machine used for the talk. Do not assume local development server availability means the research pipeline works.
- Clearly label the campaign as bounded and discuss uneven source/category coverage, the absent environment category, and unchecked near-duplicates.

## Rehearsed local demo runbook

The 13 November 2026 rehearsal used the configured local environment, existing
MongoDB and Weaviate services, local snapshot/topic artifacts and a browser at
`http://127.0.0.1:3000`. It did not test a fresh clone or the entire pipeline
from crawling. Start with the instructions in [setup.md](setup.md), then:

1. Confirm API readiness and database health with `curl -i
   http://localhost:8000/` and `curl -i http://localhost:8000/api/health`.
2. Open Search and use the frozen rehearsal query `test-en-05`:
   “Find Hindi coverage explaining why October inflation crossed the central
   bank’s tolerance ceiling.” Select Hindi results and show Keyword, Semantic
   and Hybrid. Point out that these are execution checks, not relevance
   judgments.
3. Open the first result's publisher URL. It returned HTTP 200 in the recorded
   rehearsal; future publisher availability can change.
4. Show Topics (11 non-noise topics, 17 outliers), then Corpus (516 articles,
   2,135 chunks, four languages, five publisher families, eight adapters).
5. Show the 48-query latency table in [VERIFICATION_REPORT.md](VERIFICATION_REPORT.md).
   It is retrieval-only latency on the recorded RTX 3050 Ti/CUDA setup, not an
   end-to-end benchmark. The score has `metrics: null`.

## Ask demo and acceptance runbook

Start MongoDB and Weaviate and follow [setup.md](setup.md). Start the API
with `NEWS_EMBED_DEVICE=cpu ./.venv/bin/python -m uvicorn api.main:app --host
127.0.0.1 --port 8000`. From `frontend/`, run
`npm run dev -- --hostname 127.0.0.1 --port 3001` and open
`http://127.0.0.1:3001/ask`. The CPU setting must be present before the
embedding singleton initializes. Confirm `/api/health` returns HTTP 200 and
the active snapshot shown in Corpus is `corpus-59b2b589fe3bbdbffdc3`.

The reviewed application questions are saved in
[`artifacts/ask_demo/questions.json`](../artifacts/ask_demo/questions.json).
The four language examples are the listed air-health (EN/HI), Kumai millet
(BN), and Gus Logie (MR) questions. For the cross-language example, ask:
“What is the Kumai village millet initiative prioritizing besides selling
crops, and how will residents incorporate millet into daily food?” The
reviewed English answer cited Bengali-only evidence about nutrition and
self-reliance, plus plans for millet momos, kachori, and noodles. The partial
answer example asks “How will Kumai residents use millet in everyday food,
and what was the initiative’s exact revenue in 2025?” The answer cites
Bengali passages for food use and identifies the missing revenue as a gap.
These examples do not establish general cross-language or answer quality.
The per-call passages and responses are in local-only
`artifacts/ask_demo/calls/` files, not committed because they contain corpus
text.

Eight calls reached the hard limit: one HTTP 503 before generation, five full
HTTP 200 answers, one HTTP 200 abstention, and one HTTP 200 partial answer.
Attempts 1 and 8 have unknown usage; both `$0.003` reservations remain
counted. Reported usage cost for attempts 2–7 is `$0.0015756`; total
reservations are `$0.024`. The attempt 7 reservation was recorded after its
call due to a harness key error. Do not use these few requests as a latency
or quality benchmark. Citation/provenance checks confirm source mapping; they
do not guarantee semantic claim support. Final user acceptance remains
pending.

For final acceptance, the user can manually submit the supported English
Kumai question above and inspect the food-use claim and its Bengali passage
citations in the UI. This is a new user-initiated request outside the recorded
implementation-test ledger and may incur normal API usage; no acceptance call
is made automatically.

The API contract has `answered`, `insufficient_evidence`,
`generation_unavailable`, and `evidence_integrity_error` outcomes; request
validation returns HTTP 422 and unavailable retrieval returns HTTP 503. The
unsupported-question injection attempt abstained but returned unrelated
citations; it does not establish general or article-passage injection
resistance. A genuine conflict example was not identified. A simulated service-unavailable
screen is optional; if shown, say that the Playwright harness intercepted a
request and rendered HTTP 503 without taking down a service. Do not describe
it as a live outage test. The former summary-unavailable state belongs to the
removed legacy endpoint.
