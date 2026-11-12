"""Search router for multilingual news retrieval."""

from __future__ import annotations

import logging
import time
from typing import Any, List, Literal, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.dependencies import get_embed_model, get_weaviate_client
from core.config import get_config
from core.retrieve import retrieve_bm25, retrieve_dense, retrieve_hybrid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    lang_filter: Optional[List[str]] = Field(None, description="Optional list of language codes: en, hi, bn, mr")
    mode: Literal["hybrid", "dense", "bm25"] = Field("hybrid", description="Retrieval mode")
    top_k: int = Field(10, ge=1, le=50, description="Number of results to return")


class SearchResult(BaseModel):
    article_id: str
    title: str
    lang: str
    source: str
    category: str
    snippet: str
    score: float
    url: Optional[str] = None
    published_at: Optional[str] = None
    snapshot_id: str


class SearchMetadata(BaseModel):
    snapshot_id: str
    requested_mode: Literal["hybrid", "dense", "bm25"]
    executed_mode: Literal["hybrid", "dense", "bm25"]
    reranker_status: Literal["disabled", "applied", "unavailable"]
    elapsed_ms: float


class SearchResponse(BaseModel):
    results: List[SearchResult]
    metadata: SearchMetadata


@router.post("/search", response_model=SearchResponse)
async def search_articles(
    payload: SearchRequest,
    request: Request,
) -> SearchResponse:
    """Execute multilingual news retrieval across hybrid, dense, or BM25 modes."""
    started = time.perf_counter()
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="query must not be empty")
    lang_filter = [l.lower() for l in payload.lang_filter] if payload.lang_filter else None
    top_k = payload.top_k
    mode = payload.mode
    active_snapshot_id = (get_config().get("active_snapshot") or {}).get("snapshot_id")
    if not active_snapshot_id:
        raise HTTPException(status_code=503, detail="Active corpus snapshot is unavailable")

    # Fetch enough ranked chunks to keep duplicate chunks from filling an article page.
    candidate_limit = min(top_k * 10, 500)
    raw_candidates: List[dict[str, Any]] = []
    weaviate_client = getattr(request.app.state, "weaviate_client", None) or get_weaviate_client(request)

    if weaviate_client is None:
        raise HTTPException(status_code=503, detail="Search index is unavailable")
    try:
        if mode in ["hybrid", "dense"]:
            embed_model = getattr(request.app.state, "embed_model", None) or get_embed_model(request)
            if embed_model is None:
                raise RuntimeError("Embedding model is unavailable")
            query_vec = embed_model.embed_query(query)
        else:
            query_vec = None

        if mode == "hybrid":
            raw_candidates = retrieve_hybrid(query_vec=query_vec, query_text=query, client=weaviate_client, top_k=candidate_limit, lang_filter=lang_filter)
        elif mode == "dense":
            raw_candidates = retrieve_dense(query_vec=query_vec, client=weaviate_client, top_k=candidate_limit, lang_filter=lang_filter)
        else:
            raw_candidates = retrieve_bm25(query_text=query, client=weaviate_client, top_k=candidate_limit, lang_filter=lang_filter)

        if any(candidate.get("snapshot_id") != active_snapshot_id for candidate in raw_candidates):
            raise RuntimeError("Search result snapshot does not match the active snapshot")
    except Exception as e:
        logger.exception("Search retrieval failed")
        raise HTTPException(status_code=503, detail="Search retrieval is unavailable") from e

    reranker = getattr(request.app.state, "rerank_model", None)
    reranker_status = "disabled" if reranker is None else "unavailable"
    if reranker is not None:
        raw_candidates, reranker_status = reranker.rerank_with_status(query, raw_candidates, top_k=candidate_limit)

    # Keep the first (best-ranked) chunk for each article.
    articles: dict[str, dict[str, Any]] = {}
    for candidate in raw_candidates:
        article_id = str(candidate.get("article_id", ""))
        if article_id:
            articles.setdefault(article_id, candidate)

    results: List[SearchResult] = []
    for c in list(articles.values())[:top_k]:
        text = c.get("text", "")
        published_at = c.get("published_at")
        results.append(SearchResult(
            article_id=str(c["article_id"]),
            title=str(c.get("title", "")),
            lang=str(c.get("lang", "en")),
            source=str(c.get("source", "news")),
            category=str(c.get("category", "general")),
            snippet=text[:250] + ("..." if len(text) > 250 else ""),
            score=float(c.get("score", 0.0)),
            url=c.get("url"),
            published_at=published_at.isoformat() if hasattr(published_at, "isoformat") else published_at,
            snapshot_id=active_snapshot_id,
        ))
    return SearchResponse(results=results, metadata=SearchMetadata(
        snapshot_id=active_snapshot_id,
        requested_mode=mode,
        executed_mode=mode,
        reranker_status=reranker_status,
        elapsed_ms=(time.perf_counter() - started) * 1000,
    ))
