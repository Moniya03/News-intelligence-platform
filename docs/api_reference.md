# API reference

Base URL: `http://localhost:8000`. OpenAPI docs are available at `/docs`; application endpoints use the `/api` prefix. Request and response bodies are JSON.

## `GET /` — readiness

Returns service identity and a readiness status. The status is `degraded` when the embedding backend or Weaviate index is unavailable and `ready` when both checks pass. It does not check MongoDB, establish that a research corpus is loaded, or show that retrieval is useful.

## `GET /api/health` — database connectivity

Checks MongoDB and Weaviate and returns `status: "ok"` only when both probes succeed, otherwise `status: "degraded"`, with individual boolean values under `services`.

## `POST /api/search`

```json
{
  "query": "solar energy policy",
  "lang_filter": ["en", "hi"],
  "mode": "hybrid",
  "top_k": 10
}
```

`query` is required. `lang_filter` is optional and supports `en`, `hi`, `bn`, `mr`. `mode` is `hybrid` (default), `dense` or `bm25`; `top_k` defaults to 10 and must be 1–50. A successful response is `{ "results": [...] }`; no matches are a valid `200` with an empty array. An unavailable index, embedding model or retrieval operation returns `503`. Scores are retrieval scores, not truth or credibility probabilities.

Each result contains `article_id`, `title`, `lang`, `source`, `category`, `snippet`, `score`, and optional `url`. These fields reflect indexed records; they do not guarantee corpus quality or source independence.

## `POST /api/chat`

Accepts `query` and optional `lang_filter` (same language codes). Response contains only `answer` and `citations`. If retrieval finds no candidates, the API returns `200` with `"Not found in the indexed articles."` and an empty citation list. If retrieval or answer generation is unavailable, it returns `503`; an answer that fails citation validation returns `502`. Chat is not an article-veracity or fact-checking service.

## `GET /api/clusters`

Returns `{ "clusters": [...] }`. An empty stored collection is a valid `200` response with an empty list. Missing or failing MongoDB storage returns `503`.

## `GET /api/clusters/{cluster_id}`

Returns stored topic metadata and paginated member articles. `page` defaults to 1; `limit` defaults to 20 and is restricted to 1–100. Unknown topic IDs return `404`; MongoDB unavailable/query errors return `503`. The API does not fabricate topics for unknown IDs.

## Scope and status

These endpoint contracts describe current code, not an end-to-end research result. The indexed corpus and UI/API acceptance gates remain incomplete. See [verification evidence](VERIFICATION_REPORT.md) and [the phased plan](OVERHAUL_PLAN.md).
