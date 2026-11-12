"""Evidence-grounded chat endpoint over retrieved corpus passages."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import get_embed_model, get_gemini_client, get_rerank_model, get_weaviate_client
from core.embed import EmbedModel
from core.rag import generate_answer, parse_citations
from core.rerank import RerankModel
from core.retrieve import retrieve_hybrid

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., description="User question in English, Hindi, Bengali, or Marathi")
    lang_filter: Optional[List[str]] = Field(None, description="Optional language filter: ['en', 'hi', 'bn', 'mr']")


class Citation(BaseModel):
    chunk_id: str
    article_id: str
    title: str
    lang: str
    source: str
    url: Optional[str] = None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    embed_model: EmbedModel = Depends(get_embed_model),
    rerank_model: RerankModel = Depends(get_rerank_model),
    weaviate_client: Any = Depends(get_weaviate_client),
    gemini_client: Optional[Any] = Depends(get_gemini_client),
) -> ChatResponse:
    """Return an answer with explicit citations to retrieved corpus passages."""
    if weaviate_client is None:
        raise HTTPException(status_code=503, detail="Search index is unavailable")
    query = payload.query.strip()
    lang_filter = [language.lower() for language in payload.lang_filter] if payload.lang_filter else None
    try:
        if embed_model is None:
            raise RuntimeError("Embedding model is unavailable")
        query_vec = embed_model.embed_query(query)
        candidates = retrieve_hybrid(
            query_vec=query_vec,
            query_text=query,
            client=weaviate_client,
            top_k=30,
            lang_filter=lang_filter,
            alpha=0.7,
        )
    except Exception as e:
        logger.exception("Chat retrieval failed")
        raise HTTPException(status_code=503, detail="Search retrieval is unavailable") from e

    if not candidates:
        return ChatResponse(answer="Not found in the indexed articles.", citations=[])

    passages = rerank_model.rerank(query=query, candidates=candidates, top_k=8) if rerank_model else candidates[:8]
    try:
        generated = generate_answer(query, passages, llm_client=gemini_client)
    except ValueError as e:
        raise HTTPException(status_code=502, detail="Answer provider returned an uncited answer") from e
    except Exception as e:
        logger.exception("Chat answer generation failed")
        raise HTTPException(status_code=503, detail="Answer generation is unavailable") from e

    citation_map = {citation["chunk_id"]: citation for citation in parse_citations(generated["answer"], passages)}
    citations = [Citation(**citation_map[chunk_id]) for chunk_id in generated["cited_chunk_ids"] if chunk_id in citation_map]
    return ChatResponse(answer=generated["answer"], citations=citations)
