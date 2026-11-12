"""Search router for multilingual news retrieval."""

from __future__ import annotations

import logging
from typing import Any, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_embed_model, get_weaviate_client
from core.dedupe import dedup_citations
from core.embed import EmbedModel
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


class SearchResponse(BaseModel):
    results: List[SearchResult]


@router.post("/search", response_model=SearchResponse)
async def search_articles(
    payload: SearchRequest,
    embed_model: EmbedModel = Depends(get_embed_model),
    weaviate_client: Any = Depends(get_weaviate_client),
) -> SearchResponse:
    """Execute multilingual news retrieval across hybrid, dense, or BM25 modes."""
    query = payload.query.strip()
    lang_filter = [l.lower() for l in payload.lang_filter] if payload.lang_filter else None
    top_k = payload.top_k
    mode = payload.mode

    raw_candidates: List[Dict[str, Any]] = []

    if weaviate_client is None:
        raise HTTPException(status_code=503, detail="Search index is unavailable")
    try:
        if mode in ["hybrid", "dense"]:
            if embed_model is None:
                raise RuntimeError("Embedding model is unavailable")
            query_vec = embed_model.embed_query(query)
        else:
            query_vec = None

        if mode == "hybrid":
            raw_candidates = retrieve_hybrid(query_vec=query_vec, query_text=query, client=weaviate_client, top_k=top_k * 2, lang_filter=lang_filter)
        elif mode == "dense":
            raw_candidates = retrieve_dense(query_vec=query_vec, client=weaviate_client, top_k=top_k * 2, lang_filter=lang_filter)
        else:
            raw_candidates = retrieve_bm25(query_text=query, client=weaviate_client, top_k=top_k * 2, lang_filter=lang_filter)
    except Exception as e:
        logger.exception("Search retrieval failed")
        raise HTTPException(status_code=503, detail="Search retrieval is unavailable") from e

    # Deduplicate citations / articles
    if raw_candidates:
        deduped = dedup_citations(raw_candidates)
        results: List[SearchResult] = []
        for c in deduped[:top_k]:
            text = c.get("text", "")
            snippet = text[:250] + "..." if len(text) > 250 else text
            results.append(
                SearchResult(
                    article_id=str(c.get("article_id", "")),
                    title=str(c.get("title", "")),
                    lang=str(c.get("lang", "en")),
                    source=str(c.get("source", "news")),
                    category=str(c.get("category", "general")),
                    snippet=snippet,
                    score=float(c.get("score", 0.0)),
                    url=c.get("url"),
                )
            )
        return SearchResponse(results=results)

    return SearchResponse(results=[])
