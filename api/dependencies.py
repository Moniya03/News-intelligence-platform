"""FastAPI dependency injection providers.

Extracts initialized model, database, and client instances from the FastAPI application state.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import Request

from core.embed import get_embed_model as _default_embed_model, EmbedModel
from core.rerank import get_rerank_model as _default_rerank_model, RerankModel
from core.rag import get_gemini_client as _default_gemini_client
from core.index import get_weaviate_client as _default_weaviate_client
from pymongo import MongoClient
from core.config import get_config


def get_embed_model(request: Request) -> EmbedModel:
    """Return the BGE-M3 embedding model from application state or global singleton."""
    model = getattr(request.app.state, "embed_model", None)
    if model is None:
        return _default_embed_model()
    return model


def get_rerank_model(request: Request) -> RerankModel:
    """Return the BGE reranker cross-encoder model from application state or global singleton."""
    model = getattr(request.app.state, "rerank_model", None)
    if model is None:
        return _default_rerank_model()
    return model


def get_mongo_db(request: Request) -> Any:
    """Return the MongoDB database instance from application state or create connection."""
    db = getattr(request.app.state, "mongo_db", None)
    if db is not None:
        return db

    cfg = get_config()
    uri = cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")
    db_name = cfg.get("mongo", {}).get("db", "news_intel")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        return client[db_name]
    except Exception:
        return None


def get_weaviate_client(request: Request) -> Any:
    """Return the Weaviate client instance from application state or create connection."""
    client = getattr(request.app.state, "weaviate_client", None)
    if client is not None:
        return client
    return _default_weaviate_client()


def get_gemini_client(request: Request) -> Optional[Any]:
    """Return the Gemini client instance from application state or create instance."""
    client = getattr(request.app.state, "gemini_client", None)
    if client is not None:
        return client
    return _default_gemini_client()
