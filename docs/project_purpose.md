# Project purpose

## Research question

Can multilingual embeddings help a reader retrieve Indian news across English, Hindi, Bengali and Marathi, and can topic clustering make a collected corpus easier to explore?

This is an NLP course project about building and evaluating a trustworthy research pipeline. Its contribution is a documented corpus, fair retrieval baselines, reproducible measurements and a clear account of limitations. It is not a fact-checking or misinformation-detection system.

## Intended users

College faculty and students reviewing the research question, corpus construction, methods and evidence. A useful presentation should let them inspect real article sources and understand what has and has not been measured.

## Current status

The active local snapshot contains 516 accepted articles and 2,135 chunks from eight adapters. Search, Topics and Corpus have passed a bounded browser/runtime rehearsal, including cached-vector recovery into an isolated scratch index. The corpus is not representative: source/category coverage is uneven, there are no environment-category articles, and near-duplicate/syndication checks remain incomplete. The held-out retrieval baseline is saved, but quality is unevaluated because its 427-pair pool has no human judgments. The project remains in progress; see [the verification report](VERIFICATION_REPORT.md) and [the roadmap](OVERHAUL_PLAN.md).

The API supports Search, optional evidence-grounded chat, topic artifacts and Corpus data. Summary provider access is unverified. The rehearsal checked the UI's summary-unavailable state; its Playwright 503 state used explicit request interception and was simulated. No retrieval-quality or chat-quality result is claimed.

## Scope boundaries

In scope: ethical and reproducible article collection, stable provenance, multilingual retrieval baselines, topic exploration and honest evaluation. Out of scope: article truth labels, source credibility scores, fake-news detection, general-purpose chat and claims of zero hallucinations.
