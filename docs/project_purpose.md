# Project purpose

## Research question

Can multilingual embeddings help a reader retrieve Indian news across English, Hindi, Bengali and Marathi, and can topic clustering make a collected corpus easier to explore?

This is an NLP course project about building and evaluating a trustworthy research pipeline. Its contribution is a documented corpus, fair retrieval baselines, reproducible measurements and a clear account of limitations. It is not a fact-checking or misinformation-detection system.

## Intended users

College faculty and students reviewing the research question, corpus construction, methods and evidence. A useful presentation should let them inspect real article sources and understand what has and has not been measured.

## Current status

The active local snapshot contains 516 accepted articles and 2,135 chunks from eight adapters. Search, Topics and Corpus have passed a bounded browser/runtime rehearsal, including cached-vector recovery into an isolated scratch index. The corpus is not representative: source/category coverage is uneven, there are no environment-category articles, and near-duplicate/syndication checks remain incomplete. The held-out retrieval baseline is saved, but quality is unevaluated because its 427-pair pool has no human judgments. The project remains in progress; see [the verification report](VERIFICATION_REPORT.md) and [the roadmap](OVERHAUL_PLAN.md).

The workspace now includes Search, Ask, Topics and Corpus. Seven of eight bounded Ask attempts returned HTTP 200: five full answers, one unsupported-question abstention, and one partial answer with an explicit gap. All seven outputs passed bounded passage/citation review across English, Hindi, Bengali and Marathi; one English answer was grounded in Bengali-only evidence. Attempt 1 returned HTTP 503 before generation. No genuine conflicting-source example was identified, and final user acceptance remains pending. Attempts 1 and 8 have unknown provider usage; their `$0.003` reservations remain counted. These examples do not establish retrieval or answer quality. Dated summary and simulated-outage checks in the verification report describe the removed legacy path.

## Scope boundaries

In scope: ethical and reproducible article collection, stable provenance, multilingual retrieval baselines, topic exploration and honest evaluation. Out of scope: article truth labels, source credibility scores, fake-news detection, general-purpose chat and claims of zero hallucinations.
