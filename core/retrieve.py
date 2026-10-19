"""Retrieval module for Multilingual News Intelligence Platform.

Executes hybrid, dense vector, and BM25 lexical searches against Weaviate with
language filtering and score normalization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CLASS_NAME = "NewsChunk"


def _format_v4_object(obj: Any, rank: int) -> Dict[str, Any]:
    """Extract standard chunk dict from Weaviate v4 query result object."""
    props = getattr(obj, "properties", {}) or {}
    metadata = getattr(obj, "metadata", None)

    score = 1.0 / (1.0 + rank)
    if metadata:
        if getattr(metadata, "score", None) is not None:
            score = float(metadata.score)
        elif getattr(metadata, "certainty", None) is not None:
            score = float(metadata.certainty)
        elif getattr(metadata, "distance", None) is not None:
            score = 1.0 - float(metadata.distance)

    chunk_id = str(props.get("chunk_index") or props.get("chunk_id") or f"{props.get('article_id', 'art')}_c000")

    return {
        "chunk_id": chunk_id,
        "article_id": str(props.get("article_id", "")),
        "text": str(props.get("text", "")),
        "title": str(props.get("title", "")),
        "lang": str(props.get("lang", "")),
        "category": str(props.get("category", "")),
        "source": str(props.get("source", "")),
        "score": float(score),
    }


def _build_v4_filter(lang_filter: Optional[List[str]]) -> Any:
    """Build Weaviate v4 Filter for language selection."""
    if not lang_filter:
        return None
    try:
        from weaviate.classes.query import Filter
        if len(lang_filter) == 1:
            return Filter.by_property("lang").equal(lang_filter[0].lower())
        else:
            return Filter.by_property("lang").contains_any([l.lower() for l in lang_filter])
    except Exception as e:
        logger.warning("Could not construct v4 Filter: %s", e)
        return None


def retrieve_hybrid(
    query_vec: np.ndarray | List[float],
    query_text: str,
    client: Any,
    top_k: int = 30,
    lang_filter: Optional[List[str]] = None,
    alpha: float = 0.7,
) -> List[Dict[str, Any]]:
    """Perform hybrid search (dense vector + BM25 keyword) in Weaviate.

    Args:
        query_vec: 1D query embedding vector.
        query_text: Raw query text for BM25.
        client: Weaviate client.
        top_k: Maximum candidates to retrieve (default 30).
        lang_filter: Optional list of language codes to filter by.
        alpha: Hybrid weighting (1.0 = pure vector, 0.0 = pure BM25, default 0.7).

    Returns:
        List of candidate chunk dictionaries with score.
    """
    if client is None:
        logger.warning("Weaviate client is None. Returning empty retrieval results.")
        return []

    vec_list = query_vec.tolist() if isinstance(query_vec, np.ndarray) else query_vec

    # 1. Try Weaviate v4 API
    if hasattr(client, "collections"):
        try:
            from weaviate.classes.query import MetadataQuery

            collection = client.collections.get(CLASS_NAME)
            filters = _build_v4_filter(lang_filter)

            res = collection.query.hybrid(
                query=query_text,
                vector=vec_list,
                alpha=alpha,
                limit=top_k,
                filters=filters,
                return_metadata=MetadataQuery(score=True),
            )
            results = [_format_v4_object(o, rank=i) for i, o in enumerate(res.objects)]
            return results
        except Exception as e:
            logger.warning("Weaviate v4 hybrid search error: %s", e)

    # 2. Try Weaviate v3 API fallback
    if hasattr(client, "query"):
        try:
            q = client.query.get(
                CLASS_NAME,
                ["article_id", "chunk_index", "text", "title", "lang", "category", "source"],
            ).with_additional(["score"])

            hybrid_dict = {"query": query_text, "vector": vec_list, "alpha": alpha}
            q = q.with_hybrid(hybrid_dict).with_limit(top_k)

            if lang_filter:
                operands = [{"path": ["lang"], "operator": "Equal", "valueText": l} for l in lang_filter]
                where_filter = (
                    operands[0]
                    if len(operands) == 1
                    else {"operator": "Or", "operands": operands}
                )
                q = q.with_where(where_filter)

            response = q.do()
            raw_items = response.get("data", {}).get("Get", {}).get(CLASS_NAME, []) or []
            results = []
            for i, item in enumerate(raw_items):
                score = 1.0 / (1.0 + i)
                add = item.get("_additional", {})
                if "score" in add:
                    try:
                        score = float(add["score"])
                    except Exception:
                        pass
                results.append({
                    "chunk_id": item.get("chunk_index", f"{item.get('article_id', 'art')}_c000"),
                    "article_id": str(item.get("article_id", "")),
                    "text": str(item.get("text", "")),
                    "title": str(item.get("title", "")),
                    "lang": str(item.get("lang", "")),
                    "category": str(item.get("category", "")),
                    "source": str(item.get("source", "")),
                    "score": score,
                })
            return results
        except Exception as e:
            logger.warning("Weaviate v3 hybrid search error: %s", e)

    return []


def retrieve_dense(
    query_vec: np.ndarray | List[float],
    client: Any,
    top_k: int = 30,
    lang_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Perform pure dense vector search in Weaviate.

    Args:
        query_vec: 1D query embedding vector.
        client: Weaviate client.
        top_k: Number of chunks to retrieve.
        lang_filter: Optional language filter list.

    Returns:
        List of retrieved chunk dicts.
    """
    if client is None:
        logger.warning("Weaviate client is None. Returning empty retrieval results.")
        return []

    vec_list = query_vec.tolist() if isinstance(query_vec, np.ndarray) else query_vec

    # 1. Try v4 API
    if hasattr(client, "collections"):
        try:
            from weaviate.classes.query import MetadataQuery

            collection = client.collections.get(CLASS_NAME)
            filters = _build_v4_filter(lang_filter)

            res = collection.query.near_vector(
                near_vector=vec_list,
                limit=top_k,
                filters=filters,
                return_metadata=MetadataQuery(distance=True, certainty=True),
            )
            return [_format_v4_object(o, rank=i) for i, o in enumerate(res.objects)]
        except Exception as e:
            logger.warning("Weaviate v4 dense search error: %s", e)

    # 2. Try v3 API fallback
    if hasattr(client, "query"):
        try:
            q = client.query.get(
                CLASS_NAME,
                ["article_id", "chunk_index", "text", "title", "lang", "category", "source"],
            ).with_additional(["distance", "certainty"]).with_near_vector({"vector": vec_list}).with_limit(top_k)

            if lang_filter:
                operands = [{"path": ["lang"], "operator": "Equal", "valueText": l} for l in lang_filter]
                where_filter = operands[0] if len(operands) == 1 else {"operator": "Or", "operands": operands}
                q = q.with_where(where_filter)

            response = q.do()
            raw_items = response.get("data", {}).get("Get", {}).get(CLASS_NAME, []) or []
            results = []
            for i, item in enumerate(raw_items):
                score = 1.0 / (1.0 + i)
                add = item.get("_additional", {})
                if "certainty" in add and add["certainty"] is not None:
                    score = float(add["certainty"])
                elif "distance" in add and add["distance"] is not None:
                    score = 1.0 - float(add["distance"])
                results.append({
                    "chunk_id": item.get("chunk_index", f"{item.get('article_id', 'art')}_c000"),
                    "article_id": str(item.get("article_id", "")),
                    "text": str(item.get("text", "")),
                    "title": str(item.get("title", "")),
                    "lang": str(item.get("lang", "")),
                    "category": str(item.get("category", "")),
                    "source": str(item.get("source", "")),
                    "score": score,
                })
            return results
        except Exception as e:
            logger.warning("Weaviate v3 dense search error: %s", e)

    return []


def retrieve_bm25(
    query_text: str,
    client: Any,
    top_k: int = 30,
    lang_filter: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Perform pure BM25 keyword search in Weaviate.

    Args:
        query_text: Keyword query string.
        client: Weaviate client.
        top_k: Number of chunks to retrieve.
        lang_filter: Optional language filter list.

    Returns:
        List of retrieved chunk dicts.
    """
    if client is None:
        logger.warning("Weaviate client is None. Returning empty retrieval results.")
        return []

    # 1. Try v4 API
    if hasattr(client, "collections"):
        try:
            from weaviate.classes.query import MetadataQuery

            collection = client.collections.get(CLASS_NAME)
            filters = _build_v4_filter(lang_filter)

            res = collection.query.bm25(
                query=query_text,
                limit=top_k,
                filters=filters,
                return_metadata=MetadataQuery(score=True),
            )
            return [_format_v4_object(o, rank=i) for i, o in enumerate(res.objects)]
        except Exception as e:
            logger.warning("Weaviate v4 BM25 search error: %s", e)

    # 2. Try v3 API fallback
    if hasattr(client, "query"):
        try:
            q = client.query.get(
                CLASS_NAME,
                ["article_id", "chunk_index", "text", "title", "lang", "category", "source"],
            ).with_additional(["score"]).with_bm25(query=query_text).with_limit(top_k)

            if lang_filter:
                operands = [{"path": ["lang"], "operator": "Equal", "valueText": l} for l in lang_filter]
                where_filter = operands[0] if len(operands) == 1 else {"operator": "Or", "operands": operands}
                q = q.with_where(where_filter)

            response = q.do()
            raw_items = response.get("data", {}).get("Get", {}).get(CLASS_NAME, []) or []
            results = []
            for i, item in enumerate(raw_items):
                score = 1.0 / (1.0 + i)
                add = item.get("_additional", {})
                if "score" in add and add["score"] is not None:
                    score = float(add["score"])
                results.append({
                    "chunk_id": item.get("chunk_index", f"{item.get('article_id', 'art')}_c000"),
                    "article_id": str(item.get("article_id", "")),
                    "text": str(item.get("text", "")),
                    "title": str(item.get("title", "")),
                    "lang": str(item.get("lang", "")),
                    "category": str(item.get("category", "")),
                    "source": str(item.get("source", "")),
                    "score": score,
                })
            return results
        except Exception as e:
            logger.warning("Weaviate v3 BM25 search error: %s", e)

    return []
