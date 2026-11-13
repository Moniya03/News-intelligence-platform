# Retrieval evaluation: protocol and current status

## What was run

The evaluation uses frozen snapshot `corpus-59b2b589fe3bbdbffdc3` (516
articles, 2,135 chunks; snapshot manifest SHA-256
`0c56de1aafcbd32d19e68f8c0b99f2f31f1f5c5e89a49cbeae20acf416bb5eb2`). The
query file is frozen at SHA-256
`6f210ec78a55b0a5ba1195767382ca153f9211ff88d1afc96a4994ffc8fbffac`.
It has 60 queries: 12 development queries and 48 held-out queries, with 15
queries in each language (English, Hindi, Bengali, Marathi). Each language has
12 held-out queries, evenly split across same-language, cross-language, and
multilingual information needs (four each). The development split has three
same-language queries per language. Queries were written from this collected
corpus and are not a representative sample of reader needs or news topics.

The held-out baseline ran each of BM25, BGE-M3 dense, and hybrid retrieval once
for every one of the 48 queries, returning up to five unique articles per
system. The development run separately ran all 12 development queries with the
same snapshot, models, candidate depth, hybrid alpha, and retrieval settings;
the held-out results did not tune those settings. No reranker comparison was
included: the baseline pool was frozen without reranking so the comparison
stays limited to the three consistently run systems.

Pooling the three held-out rankings produced 427 unique query/article pairs
(720 possible ranking slots before cross-system overlap). The blinded local
helper packet has SHA-256
`5157a4bb1e3e68ad41020ec9711daf99985516586a1f4da9dbc7e804c59a6aa9`.
Each packet row contains a query, language, randomized candidate ID, title,
publisher URL, and a short excerpt. It omits system names and ranks. The packet
is local and ignored by Git; it is an aid to judging, not a corpus export. It
contains no full article bodies. Do not redistribute raw article text or
images.

The saved retrieval-only mean latency per query is:

| Split | BM25 | Dense | Hybrid |
| --- | ---: | ---: | ---: |
| Held-out, 48 queries | 30.623 ms | 79.412 ms | 85.717 ms |
| Development, 12 queries | 30.556 ms | 107.432 ms | 114.843 ms |

These are observed local timings, not end-to-end API/UI latency or a hardware
benchmark. Dense and hybrid include query embedding time; BM25 does not. The
run used BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181`,
FlagEmbedding on CUDA fp16, an NVIDIA RTX 3050 Ti Laptop GPU, candidate depth
150 chunks, and top five unique articles. Batch size was one. Timings depend on
GPU load, warmup/cache state, and local services, so treat them as descriptive.

## Human relevance judgments

Judge the 427 distinct held-out query/article pairs, not individual system
slots. Assign every pair to one language-capable helper and double-judge at
least `ceil(0.20 × 427) = 86` pairs, for at least 513 initial decisions before
adjudication. The packet is already blinded and candidates are shuffled within
each query. Do not reveal system names or ranking positions to helpers.

Use this rubric against the query's stated intent and evidence expectations:

| Grade | Meaning |
| ---: | --- |
| 0 | Not relevant: does not provide evidence that helps satisfy the information need. |
| 1 | Partially relevant: related, but only supports part of the need or lacks a key requested detail. |
| 2 | Highly relevant: directly supports the main information need with useful evidence. |

Judge the supplied title and excerpt. Use the publisher URL for context only
when the excerpt is insufficient and the helper can access it normally. Mark a
pair `unjudgeable` if the language or evidence cannot be assessed; do not guess.
Do not paste article text into the shared judgment file. Record one JSON object
per helper decision in `data/retrieval_eval/corpus-59b2b589fe3bbdbffdc3/judgments.jsonl`
(this file is local/ignored):

```json
{"query_id":"test-en-01","candidate_id":"c001","judge_id":"helper-1","grade":2,"status":"judged"}
{"query_id":"test-en-01","candidate_id":"c002","judge_id":"helper-2","grade":null,"status":"unjudgeable"}
```

`status` is `judged` or `unjudgeable`; judged grades must be integer 0, 1,
or 2. Use a stable pseudonymous helper ID, not a person's name or contact
details. For every disagreement, add the same adjudication result to each
decision row for that pair:

```json
{"query_id":"test-en-01","candidate_id":"c001","judge_id":"helper-1","grade":2,"status":"judged","adjudicated_status":"judged","adjudicated_grade":1,"adjudicator_id":"adjudicator-1"}
```

Adjudication may resolve a grade difference or a `judged` versus
`unjudgeable` conflict. Set `adjudicated_status` to `unjudgeable` and
`adjudicated_grade` to `null` if the pair cannot be assessed. Keep the original
decisions in the file; do not replace them with the adjudicated label.

The scorer reports per-query and macro nDCG@5, MRR@5, and pooled Recall@5,
plus language × information-need strata, raw double-judge agreement,
disagreement/adjudication counts, and latency. nDCG uses grades 0–2 and the
judged pool as its ideal ranking; MRR counts the first grade ≥1 in the top five;
pooled Recall@5 is relevant retrieved articles divided by relevant articles in
this judged pool. It is not exhaustive corpus recall. Queries with no judged
relevant candidates have undefined relevance metrics and are counted in the
report; never turn missing denominators into zero performance. Report the
judged-pair and query denominators with any metric.

## Reproduction and handoff

From the repository root, after the verified snapshot, Weaviate index, and
project Python environment are available:

```bash
make eval-retrieval ACTION=validate
make eval-retrieval ACTION=run
make eval-retrieval ACTION="run --split dev --output artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/dev_baseline.json"
make eval-retrieval ACTION="pool --run artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json"
make eval-retrieval ACTION="score --run artifacts/retrieval_eval/v1/runs/corpus-59b2b589fe3bbdbffdc3/baseline.json --pool artifacts/retrieval_eval/v1/pools/corpus-59b2b589fe3bbdbffdc3/pool.json --judgments data/retrieval_eval/corpus-59b2b589fe3bbdbffdc3/judgments.jsonl"
```

`ACTION=run` defaults to held-out `test`; the dev run requires an explicit
`--split dev`. `pool` writes the blinded packet under the ignored `data/`
directory. Helpers need only the packet plus the rubric above and should return
the JSONL decisions. After saving judgments at the path above, rerun the final
`score` command. The current score remains `incomplete` with `metrics: null`
until all pooled pairs are judged, at least 20% are double-judged, and every
disagreement is adjudicated. The scoring command must not be presented as a
retrieval-quality result before then.

The current saved artifacts are `baseline.json` (SHA-256
`64261101c7c613dcbe7f5e6e459ff8e405076aca99b212aa0df81d8c91835651`),
`dev_baseline.json` (SHA-256
`45f73d0ee207f379b2b125b817746957a2b5e30479a342a3162e148b1263b0d2`),
`pool.json` (SHA-256
`efdbe250bf37b9e91ad25933320e4d1ccfc582b113a69bc13715cdefbaafe993`), and
`scores.json` (SHA-256
`f6bea89c99ca52140774ab24f28b39fffc0fbe2a8085aba5c54aa1187126dd25`).
The score records 427 pairs and explicitly says human judgments are
unavailable. There are no qrels or retrieval-quality metrics yet.
