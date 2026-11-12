"""Snapshot-scoped topic API backed only by verified immutable artifacts."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.snapshot_evidence import load_active_snapshot
from core.config import get_config
from core.snapshot_topics import load_active_topic_run

router = APIRouter(tags=["clusters"])


class Cluster(BaseModel):
    id: int
    label: str
    size: int
    lang_counts: dict[str, int]
    source_counts: dict[str, int]
    top_terms: list[str]
    representative_article_ids: list[str]


class Article(BaseModel):
    article_id: str
    title: str
    lang: str
    source: str
    category: str
    url: str | None = None
    published_at: str


class ClustersListResponse(BaseModel):
    snapshot_id: str
    run_id: str | None
    settings_hash: str | None
    algorithm: str | None
    topic_count: int
    outlier_count: int
    clusters: list[Cluster]


class ClusterDetailResponse(BaseModel):
    snapshot_id: str
    run_id: str
    settings_hash: str
    articles: list[Article]
    total: int
    cluster: Cluster


def _load_topics() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, list[dict[str, Any]]]:
    try:
        manifest, articles = load_active_snapshot()
        result = load_active_topic_run(
            manifest["snapshot_id"], [article["article_id"] for article in articles], get_config(),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Verified snapshot topic data is unavailable") from exc
    if result is None:
        return manifest, articles, None, []
    run, topics = result
    return manifest, articles, run, topics


def _cluster(document: dict[str, Any]) -> Cluster:
    return Cluster(
        id=int(document["id"]), label=str(document["label"]), size=int(document["size"]),
        lang_counts=document["lang_counts"], source_counts=document["source_counts"],
        top_terms=document["top_terms"], representative_article_ids=document["representative_article_ids"],
    )


@router.get("/clusters", response_model=ClustersListResponse)
async def list_clusters() -> ClustersListResponse:
    """List topics for the active snapshot; a missing run is a valid empty result."""
    manifest, _, run, topics = _load_topics()
    return ClustersListResponse(
        snapshot_id=manifest["snapshot_id"],
        run_id=run["run_id"] if run else None,
        settings_hash=run["settings_hash"] if run else None,
        algorithm=run["algorithm"] if run else None,
        topic_count=run["topic_count"] if run else 0,
        outlier_count=run["outlier_count"] if run else 0,
        clusters=[_cluster(topic) for topic in topics],
    )


@router.get("/clusters/{cluster_id}", response_model=ClusterDetailResponse)
async def get_cluster_details(
    cluster_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Page size limit"),
) -> ClusterDetailResponse:
    """Return real frozen articles assigned to a topic, including the -1 noise group."""
    manifest, articles, run, topics = _load_topics()
    if run is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    topic = next((item for item in topics if int(item["id"]) == cluster_id), None)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    article_by_id = {article["article_id"]: article for article in articles}
    member_ids = topic["article_ids"]
    selected = member_ids[(page - 1) * limit:page * limit]
    return ClusterDetailResponse(
        snapshot_id=manifest["snapshot_id"], run_id=run["run_id"], settings_hash=run["settings_hash"],
        articles=[
            Article(
                article_id=article_id,
                title=article_by_id[article_id]["title"],
                lang=article_by_id[article_id]["lang"],
                source=article_by_id[article_id]["source_family"],
                category=article_by_id[article_id].get("category", ""),
                url=article_by_id[article_id].get("original_url") or article_by_id[article_id].get("canonical_url"),
                published_at=str(article_by_id[article_id]["published_at"]),
            )
            for article_id in selected
        ],
        total=len(member_ids),
        cluster=_cluster(topic),
    )
