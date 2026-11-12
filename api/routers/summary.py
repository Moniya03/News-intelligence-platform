"""Optional evidence summary API; generation is disabled until provider access is verified."""

from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.snapshot_evidence import load_active_snapshot

router = APIRouter(tags=["summary"])


class SummaryRequest(BaseModel):
    query: str = Field(min_length=1)
    article_ids: list[str] = Field(min_length=1, max_length=10)
    snapshot_id: str = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value

    @field_validator("article_ids")
    @classmethod
    def valid_article_ids(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in values):
            raise ValueError("article_ids must be SHA-256 article IDs")
        if len(set(values)) != len(values):
            raise ValueError("article_ids must be distinct")
        return values


class Citation(BaseModel):
    citation_id: str
    article_id: str
    title: str
    url: str | None
    source: str
    lang: str


class SummaryResponse(BaseModel):
    status: Literal["available", "unavailable", "insufficient_evidence"]
    summary: str | None
    citations: list[Citation]
    snapshot_id: str
    reason: str | None


@router.post("/search/summary", response_model=SummaryResponse)
async def summarize(payload: SummaryRequest) -> SummaryResponse:
    try:
        manifest, articles = load_active_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Active corpus snapshot is unavailable or invalid") from exc
    if payload.snapshot_id != manifest["snapshot_id"]:
        raise HTTPException(status_code=409, detail="Snapshot does not match the active corpus")

    by_id = {article["article_id"]: article for article in articles}
    missing = [article_id for article_id in payload.article_ids if article_id not in by_id]
    if missing:
        raise HTTPException(status_code=404, detail="One or more article IDs are not in the active snapshot")

    evidence = [by_id[article_id] for article_id in payload.article_ids]
    evidence = [article for article in evidence if len(str(article.get("body", "")).strip()) >= 200]
    citations = [Citation(
        citation_id=f"S{index}",
        article_id=article["article_id"],
        title=article["title"],
        url=article.get("canonical_url") or article.get("original_url"),
        source=article["source_family"],
        lang=article["lang"],
    ) for index, article in enumerate(evidence, 1)]
    return SummaryResponse(
        status="unavailable" if evidence else "insufficient_evidence",
        summary=None,
        citations=citations,
        snapshot_id=manifest["snapshot_id"],
        reason="provider_access_unverified" if evidence else "insufficient_evidence",
    )
