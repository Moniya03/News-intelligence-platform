# Product scope and requirements

This document replaces the earlier product draft. The earlier draft proposed misinformation scoring, credibility labels, simulated evaluation targets and unsupported feature claims; those are not part of the current project scope and their numbers must not be presented as results.

## Product goal

Create a faculty-reviewable NLP research demo for this question: **Can multilingual retrieval help find Indian news across English, Hindi, Bengali and Marathi, and can topic clustering help browse the corpus?**

## Required evidence

- Real articles with original publisher URLs and traceable collection provenance.
- A documented corpus snapshot and visible language/source/category coverage.
- Comparable BM25, dense and hybrid retrieval evaluations over the same data and query set.
- Measured results with methods, limitations and reproducible commands.
- Topic browsing only when backed by actual stored output; no invented clusters or article examples.

## Current status

A bounded pilot verified eight source-language spiders and Mongo persistence, plus local model execution. The frozen corpus, Search/Ask/Topics/Corpus workspace, and retrieval-evaluation engineering are in place; held-out retrieval relevance still lacks human judgments. Seven of eight bounded Ask attempts returned HTTP 200: five full answers, one unsupported-question abstention, and one partial answer. The seven outputs passed passage/citation review across English, Hindi, Bengali and Marathi, including one English answer grounded in Bengali-only evidence; attempt 1 returned HTTP 503 before generation. Final user acceptance remains pending. See [the roadmap](OVERHAUL_PLAN.md) and [verification report](VERIFICATION_REPORT.md).

## Deferred or excluded

Misinformation detection, credibility scoring, consensus scores, fake verification badges, general chat, Airflow scheduling, model training and an in-app experiments dashboard are excluded from the current scope. Ask is a limited cited-Q&A demo, not a fact checker or a measured answer-quality result.
