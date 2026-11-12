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

A bounded pilot verified eight source-language spiders and Mongo persistence, plus local model execution. It does not yet meet the roadmap's corpus or evaluation acceptance criteria. The API, frontend and remaining research slices are still being integrated. See [the roadmap](OVERHAUL_PLAN.md) and [verification report](VERIFICATION_REPORT.md).

## Deferred or excluded

Misinformation detection, credibility scoring, consensus scores, fake verification badges, general chat, Airflow scheduling, model training and an in-app experiments dashboard are excluded from the current scope. Chat is a limited evidence-grounded API capability, not a research result or core project claim.
