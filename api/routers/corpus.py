"""Snapshot-scoped corpus coverage API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.snapshot_evidence import corpus_summary, load_active_snapshot

router = APIRouter(tags=["corpus"])


class CorpusResponse(BaseModel):
    snapshot_id: str
    article_count: int
    chunk_count: int
    language_counts: dict[str, int]
    source_counts: dict[str, int]
    source_adapter_counts: dict[str, int]
    category_counts: dict[str, int]
    coverage: dict[str, dict[str, dict[str, int]]]
    published_from: str
    published_to: str
    last_successful_crawl_at: str | None
    collection_status: str
    collection_name: str | None
    topic_counts: dict[str, int] | None
    topic_status: str
    rejected_count: int | None
    crawl_status: str
    duplicate_count: int | None


@router.get("/corpus", response_model=CorpusResponse)
async def get_corpus() -> CorpusResponse:
    """Report verified frozen-snapshot facts and explicitly unavailable operations."""
    try:
        manifest, articles = load_active_snapshot()
        return CorpusResponse(**corpus_summary(manifest, articles))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Active corpus snapshot is unavailable or invalid") from exc
