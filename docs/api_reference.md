# API reference

Base URL: `http://localhost:8000`. OpenAPI docs are at `/docs`; application endpoints use the `/api` prefix. Request and response bodies are JSON.

## `GET /` — readiness

Returns service identity and readiness. `ready` means the embedding backend and Weaviate index are configured and available; it does not establish corpus quality or useful retrieval.

## `GET /api/health` — database connectivity

Returns `status: "ok"` only when MongoDB and Weaviate probes succeed, otherwise `status: "degraded"`, with booleans under `services`. This is a connectivity check, not a corpus or retrieval-quality check.

## `POST /api/search`

Request:

```json
{
  "query": "solar energy policy",
  "lang_filter": ["en", "hi"],
  "mode": "hybrid",
  "top_k": 10
}
```

`query` is required and cannot be blank. `lang_filter` is optional; supported language codes are `en`, `hi`, `bn`, and `mr`. `mode` is `hybrid` (default), `dense`, or `bm25`; `top_k` defaults to 10 and must be 1–50. BM25 does not load or call the embedding model. Dense and hybrid embed the query and require the embedding backend.

Successful responses have `results` and `metadata`:

```json
{
  "results": [
    {
      "article_id": "<sha256>",
      "title": "Example headline",
      "lang": "en",
      "source": "example-source",
      "category": "politics",
      "snippet": "Indexed article text...",
      "score": 0.73,
      "url": "https://example.org/article",
      "published_at": "2026-11-01T12:00:00Z",
      "snapshot_id": "corpus-59b2b589fe3bbdbffdc3"
    }
  ],
  "metadata": {
    "snapshot_id": "corpus-59b2b589fe3bbdbffdc3",
    "requested_mode": "hybrid",
    "executed_mode": "hybrid",
    "reranker_status": "disabled",
    "elapsed_ms": 12.3
  }
}
```

Results are unique articles, retaining each article's best-ranked chunk as its snippet. `url` and `published_at` may be null. `reranker_status` is `applied`, `unavailable`, or `disabled`; unavailable inference preserves retrieval order and score. Scores are retrieval scores, not truth or credibility probabilities. No matches are a valid `200` with an empty `results` list. Blank queries return `422`; a missing active snapshot or index, missing embedding model for dense/hybrid, or retrieval failure returns `503`. Results from a snapshot other than the active snapshot are rejected as retrieval failures.

## `GET /api/corpus`

Returns verified facts from the active immutable snapshot and explicitly labels unavailable operations. For snapshot `corpus-59b2b589fe3bbdbffdc3`, the response reports 516 articles, 2,135 chunks, and language counts `en: 123`, `hi: 116`, `bn: 156`, `mr: 121`, alongside source, adapter, weak category, and adapter/category counts and publication date bounds. With the verified Slice 07 run active, `topic_status` is `"generated"` and `topic_counts` maps topic IDs to article counts, including `"-1": 17` for outliers; the 11 discovered topics plus outliers account for all 516 articles.

`collection_status: "configured"` reports the configured index collection; it is not a live index-health check. When no verified topic run exists for the active snapshot, `topic_counts` is `null` and `topic_status` is `"not_generated"`; invalid/unavailable topic artifacts set `topic_status` to `"unavailable"`. `rejected_count` and `last_successful_crawl_at` are `null`, and `crawl_status` is `"unavailable"`: campaign rejection/crawl-run records cannot be linked rigorously to this frozen snapshot. Snapshot load, identity, or checksum failure returns `503`.

## `POST /api/ask`

Accepts one independent question:

```json
{ "question": "What health risks do reports about Delhi-NCR's toxic air describe?" }
```

The question is trimmed, must not be blank, and is limited to 2,000 Unicode code points. Invalid questions return `422`; unavailable retrieval returns `503`. Ask embeds the original question and calls the existing hybrid retrieval once across all corpus languages (`alpha=0.7`, up to 30 candidates, no reranking). The workflow verifies all retrieved candidates against the active snapshot and its authoritative chunk/article data before generation, and checks the active snapshot again before returning. At most 8 complete passages and 12,000 UTF-8 bytes of serialized prompt are sent to `gpt-6-luna`; generation has a 1,024-token output cap, 45-second timeout and disabled SDK retries. The prompt instructs the model to use only retrieved passages. There is no translation, query fanout, chat history, tools, or outside source access. Prompt instructions do not guarantee semantic claim support.

Responses contain `status`, `answer_segments`, `gap`, `citations`, and `snapshot_id`; `reason` is included for unavailable generation. Each answer segment has text and one or more `citation_ids`. Citations are built by the server from trusted snapshot data and contain `citation_id`, `chunk_id`, `article_id`, the exact `passage`, `url`, `title`, `source`, `language`, and `published_at`. The client renders text as text and links only HTTP(S) article URLs.

Possible statuses:

- `answered`: checked answer segments, with citation IDs that resolve to returned citations. `gap` can identify unanswered parts.
- `insufficient_evidence`: the corpus returned no evidence, or generation abstained; no unsupported factual answer is returned.
- `generation_unavailable`: provider failure, an invalid/incomplete model response, or a prompt context limit. The response includes validated evidence when available, but no partial answer. `reason` identifies the failure.
- `evidence_integrity_error`: snapshot/chunk/article provenance failed. No answer or citations are returned.

For example, generation failure retains validated source evidence:

```json
{
  "status": "generation_unavailable",
  "answer_segments": [],
  "gap": null,
  "citations": [
    {
      "citation_id": "C1",
      "chunk_id": "<snapshot-chunk-id>",
      "article_id": "<sha256>",
      "passage": "<exact indexed passage>",
      "url": "https://example.org/article",
      "title": "Example headline",
      "source": "example-source",
      "language": "en",
      "published_at": "2026-11-01T12:00:00Z"
    }
  ],
  "snapshot_id": "corpus-59b2b589fe3bbdbffdc3",
  "reason": "provider_unavailable"
}
```

Citation and provenance validation establishes identity and source mapping, not semantic support for each generated claim. The application provides no runtime semantic guarantee or measured retrieval/answer quality. For source and evidence limits, see the [Ask design](design.md) and [verification report](VERIFICATION_REPORT.md).

## `GET /api/clusters` and `GET /api/clusters/{cluster_id}`

Both routes read verified local topic artifacts for the active immutable snapshot; they do not query or write generic MongoDB cluster records. The list response contains `snapshot_id`, nullable `run_id`, nullable `settings_hash`, nullable `algorithm`, `topic_count` (discovered non-outlier topics), `outlier_count`, and `clusters`. With no active run, it returns `200` with null run provenance, zero counts and an empty `clusters` list.

Each cluster has `id`, `label`, `size`, `lang_counts`, `source_counts`, `top_terms` and `representative_article_ids`. HDBSCAN outliers use ID `-1` and are exposed as an ordinary cluster with label `"Unassigned"`; `outlier_count` is the article count in that group. For the active run on `corpus-59b2b589fe3bbdbffdc3`, `algorithm` is `"bertopic"`, there are 11 discovered topics and 17 outliers.

The detail response contains `snapshot_id`, `run_id`, `settings_hash`, the requested `cluster`, its full `total`, and the paginated `articles` (`page` defaults to 1; `limit` defaults to 20 and must be 1–100). Article entries expose `article_id`, `title`, `lang`, `source`, `category`, nullable `url`, and `published_at`. Unknown topic IDs (including any ID when no run exists) return `404`; invalid, missing, or checksum-mismatched snapshot/topic artifacts return `503`.

## Scope and status

These contracts describe current API behavior, not a retrieval-quality result. Search relevance remains unevaluated; Ask's bounded app review is recorded separately and does not establish answer quality. Topic comparison is measured only against weak publisher-section labels; agreement is not evidence of event coherence or factual truth. See [verification evidence](VERIFICATION_REPORT.md) and [the phased plan](OVERHAUL_PLAN.md).
