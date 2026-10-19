"""Clusters router for Multilingual News Intelligence Platform.

Handles GET /api/clusters and GET /api/clusters/{cluster_id} with MongoDB retrieval
and rich mock demo fallbacks for uninitialized databases.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.dependencies import get_mongo_db
from core.cluster import get_cluster_articles, get_clusters

logger = logging.getLogger(__name__)

router = APIRouter(tags=["clusters"])


class LangCounts(BaseModel):
    en: int = 0
    hi: int = 0
    bn: int = 0
    ta: int = 0


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


MOCK_CLUSTERS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "label": "Renewable Energy & Power Grid Modernization",
        "size": 340,
        "lang_counts": {"en": 120, "hi": 110, "bn": 60, "ta": 50},
        "top_terms": ["solar", "renewable", "grid", "transmission", "energy"],
    },
    {
        "id": 2,
        "label": "Agricultural Technology & Rural Subsidies",
        "size": 285,
        "lang_counts": {"en": 65, "hi": 130, "bn": 55, "ta": 35},
        "top_terms": ["agriculture", "budget", "farmers", "irrigation", "crops"],
    },
    {
        "id": 3,
        "label": "IT Infrastructure & Regional Startups",
        "size": 210,
        "lang_counts": {"en": 80, "hi": 30, "bn": 70, "ta": 30},
        "top_terms": ["technology", "software", "startup", "investment", "park"],
    },
    {
        "id": 4,
        "label": "Space Exploration & Deep-Sea Oceanography",
        "size": 175,
        "lang_counts": {"en": 60, "hi": 35, "bn": 25, "ta": 55},
        "top_terms": ["space", "ocean", "satellite", "mission", "research"],
    },
    {
        "id": 5,
        "label": "Semiconductor Manufacturing & Supply Chains",
        "size": 190,
        "lang_counts": {"en": 90, "hi": 40, "bn": 30, "ta": 30},
        "top_terms": ["semiconductor", "chip", "manufacturing", "supply", "trade"],
    },
]

MOCK_CLUSTER_ARTICLES: Dict[int, List[Dict[str, Any]]] = {
    1: [
        {
            "article_id": "en_000101",
            "title": "India Advances Clean Energy Infrastructure with New Grid Modernization Initiative",
            "lang": "en",
            "source": "l3cube-indicnews",
            "category": "technology",
            "url": "https://news.example.com/clean-energy-grid",
        },
        {
            "article_id": "hi_000102",
            "title": "सौर ऊर्जा ग्रिड विस्तार: पश्चिमी राज्यों में अंतर्राज्यीय पारेषण परियोजना का शुभारंभ",
            "lang": "hi",
            "source": "l3cube-indicnews",
            "category": "energy",
            "url": "https://news.example.com/solar-grid-hi",
        },
        {
            "article_id": "bn_000103",
            "title": "সৌরবিদ্যুৎ পরিকাঠামো উন্নয়নে নতুন বিনিয়োগের ঘোষণা রাজ্যের",
            "lang": "bn",
            "source": "l3cube-indicnews",
            "category": "energy",
            "url": "https://news.example.com/solar-bn",
        },
        {
            "article_id": "ta_000104",
            "title": "புதுப்பிக்கத்தக்க எரிசக்தி விநியோக வலையமைப்பு நவீனமயமாக்கல் திட்டம் அறிவிப்பு",
            "lang": "ta",
            "source": "l3cube-indicnews",
            "category": "technology",
            "url": "https://news.example.com/grid-modernization-ta",
        },
    ]
}


@router.get("/clusters", response_model=ClustersListResponse)
async def list_clusters(mongo_db: Any = Depends(get_mongo_db)) -> ClustersListResponse:
    """List all topic and event clusters across the multilingual corpus."""
    clusters_data: List[Dict[str, Any]] = []

    if mongo_db is not None:
        try:
            docs = list(mongo_db["clusters"].find({}))
            for d in docs:
                clusters_data.append({
                    "id": int(d.get("id", d.get("_id", 0))),
                    "label": str(d.get("label", "General Topic")),
                    "size": int(d.get("size", 0)),
                    "lang_counts": d.get("lang_counts", {"en": 0, "hi": 0, "bn": 0, "ta": 0}),
                    "top_terms": d.get("top_terms", []),
                })
        except Exception as e:
            logger.warning("MongoDB cluster query failed: %s", e)

    if not clusters_data:
        logger.info("Using mock clusters fallback.")
        clusters_data = MOCK_CLUSTERS

    clusters = [
        Cluster(
            id=c["id"],
            label=c["label"],
            size=c["size"],
            lang_counts=LangCounts(**c["lang_counts"]),
            top_terms=c["top_terms"],
        )
        for c in clusters_data
    ]
    return ClustersListResponse(clusters=clusters)


@router.get("/clusters/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster_details(
    cluster_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
    mongo_db: Any = Depends(get_mongo_db),
) -> ClusterDetailResponse:
    """Retrieve detailed metadata and paginated articles for a cluster."""
    if mongo_db is not None:
        try:
            c_doc = mongo_db["clusters"].find_one({"$or": [{"_id": cluster_id}, {"id": cluster_id}]})
            if c_doc:
                cluster_obj = Cluster(
                    id=int(c_doc.get("id", c_doc.get("_id", cluster_id))),
                    label=str(c_doc.get("label", f"Cluster {cluster_id}")),
                    size=int(c_doc.get("size", 0)),
                    lang_counts=LangCounts(**c_doc.get("lang_counts", {"en": 0, "hi": 0, "bn": 0, "ta": 0})),
                    top_terms=c_doc.get("top_terms", []),
                )

                query = {"cluster_id": cluster_id}
                total = mongo_db["articles"].count_documents(query)
                skip = max(0, (page - 1) * limit)
                cursor = mongo_db["articles"].find(query).skip(skip).limit(limit)

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
                return ClusterDetailResponse(articles=articles, total=total, cluster=cluster_obj)
        except Exception as e:
            logger.warning("Error fetching cluster details from MongoDB: %s", e)

    # Fallback mock details
    matching_mock = next((m for m in MOCK_CLUSTERS if m["id"] == cluster_id), None)
    if not matching_mock:
        matching_mock = {
            "id": cluster_id,
            "label": f"Cluster {cluster_id}: General Current Affairs",
            "size": 42,
            "lang_counts": {"en": 15, "hi": 12, "bn": 8, "ta": 7},
            "top_terms": ["development", "initiative", "regional", "policy"],
        }

    mock_arts = MOCK_CLUSTER_ARTICLES.get(cluster_id, MOCK_CLUSTER_ARTICLES[1])
    articles = [Article(**a) for a in mock_arts]

    cluster_obj = Cluster(
        id=matching_mock["id"],
        label=matching_mock["label"],
        size=matching_mock["size"],
        lang_counts=LangCounts(**matching_mock["lang_counts"]),
        top_terms=matching_mock["top_terms"],
    )

    return ClusterDetailResponse(
        articles=articles,
        total=len(articles),
        cluster=cluster_obj,
    )
