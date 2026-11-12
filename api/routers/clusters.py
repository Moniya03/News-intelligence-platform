"""Topic cluster API backed by the MongoDB corpus."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.dependencies import get_mongo_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["clusters"])


class LangCounts(BaseModel):
    en: int = 0
    hi: int = 0
    bn: int = 0
    mr: int = 0


class Cluster(BaseModel):
    id: int
    label: str
    size: int
    lang_counts: LangCounts
    top_terms: List[str]


class Article(BaseModel):
    article_id: str
    title: str
    lang: str
    source: str
    category: str
    url: Optional[str] = None


class ClustersListResponse(BaseModel):
    clusters: List[Cluster]


class ClusterDetailResponse(BaseModel):
    articles: List[Article]
    total: int
    cluster: Cluster


def _cluster(document: Dict[str, Any], fallback_id: int = 0) -> Cluster:
    return Cluster(
        id=int(document.get("id", document.get("_id", fallback_id))),
        label=str(document.get("label", "General Topic")),
        size=int(document.get("size", 0)),
        lang_counts=LangCounts(**document.get("lang_counts", {})),
        top_terms=document.get("top_terms", []),
    )


@router.get("/clusters", response_model=ClustersListResponse)
async def list_clusters(mongo_db: Any = Depends(get_mongo_db)) -> ClustersListResponse:
    """List clusters; an empty collection is a valid empty result."""
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="Topic store is unavailable")
    try:
        clusters = [_cluster(d) for d in mongo_db["clusters"].find({})]
    except Exception as e:
        logger.exception("MongoDB cluster query failed")
        raise HTTPException(status_code=503, detail="Topic store is unavailable") from e
    return ClustersListResponse(clusters=clusters)


@router.get("/clusters/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster_details(
    cluster_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    mongo_db: Any = Depends(get_mongo_db),
) -> ClusterDetailResponse:
    """Retrieve detailed metadata and paginated articles for a cluster."""
    if mongo_db is None:
        raise HTTPException(status_code=503, detail="Topic store is unavailable")
    try:
        document = mongo_db["clusters"].find_one({"$or": [{"_id": cluster_id}, {"id": cluster_id}]})
        if document is None:
            raise HTTPException(status_code=404, detail="Topic not found")

        cluster = _cluster(document, cluster_id)
        query = {"cluster_id": cluster_id}
        total = mongo_db["articles"].count_documents(query)
        cursor = mongo_db["articles"].find(query).skip((page - 1) * limit).limit(limit)
        articles = [
            Article(
                article_id=str(doc.get("_id", doc.get("article_id", ""))),
                title=str(doc.get("title", "")),
                lang=str(doc.get("lang", "en")),
                source=str(doc.get("source", "news")),
                category=str(doc.get("category", "general")),
                url=doc.get("url"),
            )
            for doc in cursor
        ]
        return ClusterDetailResponse(articles=articles, total=total, cluster=cluster)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("MongoDB cluster detail query failed")
        raise HTTPException(status_code=503, detail="Topic store is unavailable") from e
