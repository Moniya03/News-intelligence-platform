# Study guide: multilingual news retrieval and grounded Ask

This guide is a compact route through the project for a demo, viva, or report
review. It describes what the code does and what the saved evidence supports;
the [verification report](VERIFICATION_REPORT.md) is the detailed evidence
record and the [roadmap](OVERHAUL_PLAN.md) tracks remaining acceptance work.

## Suggested study path

1. Read the [problem statement](problem_statement.md): retrieval across English,
   Hindi, Bengali and Marathi is a hypothesis to test, not a result.
2. Trace collection, immutable data and indexing in
   [architecture](architecture.md) and [setup](setup.md).
3. Learn the baselines and the human-labeling protocol in
   [retrieval evaluation](retrieval_evaluation.md).
4. Review topic exploration and its weak-label limits in the
   [verification report](VERIFICATION_REPORT.md).
5. Trace a question through [`api/ask.py`](../api/ask.py),
   [`core/retrieve.py`](../core/retrieve.py),
   [`api/routers/ask.py`](../api/routers/ask.py), and the
   [Ask API contract](api_reference.md#post-apiask).
6. Rehearse the [presentation guide](presentation_guide.md), including its
   startup checks, fallback and shutdown steps.

## Architecture in one pass

Eight bounded Scrapy adapters collected publisher articles into MongoDB. The
research snapshot freezes 516 accepted articles as 2,135 chunks with source,
article and chunk provenance. BGE-M3 embeddings are stored in a
snapshot-specific Weaviate collection. The four workspace screens are Search,
Ask, Topics and Corpus. Search compares lexical BM25, dense vector and hybrid
retrieval; Ask retrieves passages and asks a language model for a bounded
answer; Topics exposes a saved BERTopic run; Corpus reports verified snapshot
coverage. Implementation paths are linked in [architecture](architecture.md).

## Retrieval concepts and design choices

- **BM25:** lexical ranking based on term overlap and term rarity. It is a
  useful baseline for exact names and words, but cross-language terms often do
  not overlap.
- **Dense retrieval:** BGE-M3 represents a query and passages as vectors so
  related meaning may match across languages. Similarity is a retrieval signal,
  not proof of relevance or truth.
- **Hybrid retrieval:** combines BM25 and dense scores. The implementation's
  `alpha=0.7` weights the dense component at 70%; it was a fixed project
  setting, not a value proven optimal by held-out judgments.
- **Chunks:** articles are split into indexed passages to fit retrieval and
  bounded model context. Chunk boundaries can omit context, so a passage is
  not always enough to establish a complete claim.
- **Snapshot and provenance:** a frozen snapshot and deterministic chunk IDs
  let the app check that each retrieved passage belongs to the active article
  set. This guards identity and data lineage, not semantic support.
- **Search reranking vs Ask:** Search may pass its candidate list through the
  cross-encoder reranker. Ask deliberately calls hybrid retrieval once on the
  original question (up to 30 candidates, no language filter, no reranking),
  then binds at most eight validated passages. The two paths should not be
  described as using identical ranking stages.
- **Topics:** BERTopic groups articles by embedding and topic representations.
  The active run has 11 non-noise topics and 17 outliers. Publisher-section
  labels are weak comparison labels; a cluster name is not a verified event
  category or a factual conclusion.
- **Ask / PocketFlow:** [`api/ask.py`](../api/ask.py) wires a fixed linear flow:
  `Retrieve → BindEvidence → Generate → ValidateResponse`. The original
  question is sent to generation with trusted passages; the server validates
  returned citation IDs and resolves citations from snapshot data. The prompt
  asks for passage-grounded answers, but prompting is not a semantic guarantee.

## Evidence and cost at a glance

| Measure | Recorded result | What it does and does not show |
| --- | --- | --- |
| Frozen corpus | 516 articles; 2,135 chunks; EN 123, HI 116, BN 156, MR 121 | Snapshot coverage, not representative coverage |
| Retrieval evaluation | 48 held-out queries; 427 pooled query/article pairs; metrics `null` | Judgments are pending; no retrieval-quality score is available |
| Ask review | 8 attempts: 1 HTTP 503 before generation; 7 HTTP 200 outputs (5 full, 1 abstention, 1 partial) | Independent passage/citation review of a small sample; not an answer-quality estimate |
| Ask provider cost | Known `$0.0015756` for attempts 2–7; attempts 1 and 8 unknown, each `$0.003` reservation retained; `$0.024` total reservations | Attempt 7's reservation was recorded after submission; see [ledger](../artifacts/ask_demo/ledger.json) for accounting details |

The reviewed cross-language example asks what the Kumai village millet
initiative prioritizes besides selling crops and how residents will use millet
in daily food. An English answer cited Bengali passages about nutrition,
self-reliance, momos, kachoris and noodles. A second question added the exact
2025 revenue; the answer gave food-use evidence and left revenue as a gap. A
separate unsupported future prediction abstained, but returned unrelated
citations. These concrete examples and their limits are documented in the
[presentation runbook](presentation_guide.md#ask-demo-and-acceptance-runbook).

## Trust boundaries and limitations

- A citation proves which stored passage the server returned. It does not
  prove every generated statement follows from that passage, that the publisher
  is correct, or that different sources agree.
- The app is not a fact checker, credibility rater, misinformation detector,
  or semantic entailment system. There is no semantic claim-support guarantee.
- The bounded injection example tested instructions inside the question only.
  It did not test malicious article passages or establish general injection
  resistance. No genuine conflicting-source example was found.
- The corpus is small and selected, with uneven source/category coverage, zero
  environment-category articles, and incomplete near-duplicate/syndication
  checks. Do not generalize the four-language counts to Indian news overall.
- The held-out retrieval pool remains unjudged. Search latency, successful
  model inference, cited examples and topic-label agreement are not substitutes
  for a judged retrieval evaluation or user study.
- A future question should not be answered as known fact when it falls outside
  the available passages; an explicit gap is the intended behavior. Review the
  [design limits](design.md) and the [verification report](VERIFICATION_REPORT.md)
  before making claims.

## Viva questions with model answers

1. **What is the research question?** Whether multilingual retrieval can help
   find Indian news across four languages, and whether topic clusters can help
   browse the collected corpus. Both are hypotheses awaiting stronger evidence.
2. **Why use BM25?** It is a transparent lexical baseline and can perform well
   for exact terms; it also reveals where word overlap limits cross-language
   search.
3. **What does dense retrieval add?** BGE-M3 vectors can match semantically
   related passages across languages, but similarity is not relevance proof.
4. **Why hybrid retrieval?** It combines lexical matching and vector
   similarity. The current 0.7 dense weight is a fixed setting, not a judged
   optimum.
5. **Why split articles into chunks?** Retrieval can select focused passages
   and keep generation context bounded. Splitting may lose context, which is
   why passage and gap behavior matter.
6. **Why freeze a snapshot?** Stable article/chunk identity makes runs
   reproducible and allows provenance checks against the active corpus.
7. **What would establish retrieval quality?** Human judgments on the frozen
   pooled pairs, double judgments for at least 20%, adjudication, then
   denominator-aware metrics by language and query type. Those judgments are
   still pending.
8. **Why are retrieval metrics null?** The 427 unique held-out query/article
   pairs have no completed human relevance labels; ranking output alone cannot
   tell which result is relevant.
9. **What do topic scores mean?** Agreement with coarse publisher-section
   labels only. They do not establish event coherence or factual topic truth.
10. **How is Ask different from Search?** Ask uses the original question for
    one hybrid retrieval over all languages without reranking, binds up to
    eight verified passages, then generates a cited response. Search has
    selectable retrieval modes and may rerank results.
11. **What does provenance validation protect?** It checks that chunks,
    articles and citations map to the active snapshot. It does not verify the
    meaning or correctness of a generated claim.
12. **Why is this not a fact checker?** The system retrieves publisher text;
    it does not independently verify events, rate sources, or establish
    consensus. A citation is inspectable evidence, not a truth certificate.
13. **What happened in the cross-language example?** An English response used
    Bengali-only millet reporting, including food-use examples. One reviewed
    case demonstrates behavior, not broad cross-language performance.
14. **How should Ask handle missing information?** Return an explicit gap or
    abstain instead of inventing a detail. The exact-revenue example showed
    this behavior for one question.
15. **Was prompt injection solved?** No. One question contained an embedded
    instruction and the model abstained, but citations were unrelated. Article
    passage attacks and general resistance were not tested.
16. **What remains before a strong research conclusion?** Complete blinded
    relevance judgments and adjudication, evaluate any reranker separately,
    improve and document corpus coverage, and run a representative user study
    for browsing and answer usefulness.
