# Project purpose

## Research question

Can multilingual embeddings help a reader retrieve Indian news across English, Hindi, Bengali and Marathi, and can topic clustering make a collected corpus easier to explore?

This is an NLP course project about building and evaluating a trustworthy research pipeline. Its contribution is a documented corpus, fair retrieval baselines, reproducible measurements and a clear account of limitations. It is not a fact-checking or misinformation-detection system.

## Intended users

College faculty and students reviewing the research question, corpus construction, methods and evidence. A useful presentation should let them inspect real article sources and understand what has and has not been measured.

## Current status

The repository contains a bounded eight-adapter Scrapy-to-Mongo pilot and verified local embedding/reranker inference. These checks establish that selected infrastructure paths run; they do not establish a representative four-language corpus, retrieval quality, useful clusters or an end-to-end research result. The overall project remains in progress. See [the verification report](VERIFICATION_REPORT.md) and [the roadmap](OVERHAUL_PLAN.md).

The API supports search, evidence-grounded chat and stored topic clusters. Search quality and chat quality have not been validated on a frozen research corpus. If the provider or index is unavailable, the service reports an error rather than presenting generated demo content as evidence.

## Scope boundaries

In scope: ethical and reproducible article collection, stable provenance, multilingual retrieval baselines, topic exploration and honest evaluation. Out of scope: article truth labels, source credibility scores, fake-news detection, general-purpose chat and claims of zero hallucinations.
