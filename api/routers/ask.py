"""Cited question answering over the active corpus snapshot."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from api.ask import run_ask
from api.dependencies import get_embed_model, get_openai_client, get_weaviate_client

router = APIRouter(tags=["ask"])


class AskRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def valid_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        if len(value) > 2000:
            raise ValueError("question must not exceed 2000 Unicode code points")
        return value


@router.post("/ask")
async def ask(payload: AskRequest, embed_model: Any = Depends(get_embed_model),
        weaviate_client: Any = Depends(get_weaviate_client),
        openai_client: Any = Depends(get_openai_client)) -> dict:
    if weaviate_client is None or embed_model is None:
        raise HTTPException(status_code=503, detail="Search retrieval is unavailable")
    try:
        return await run_ask(payload.question, embed_model, weaviate_client, openai_client)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Search retrieval is unavailable") from exc
