"""Health check router for Multilingual News Intelligence Platform.

Handles GET /api/health with status probes for MongoDB and Weaviate.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.dependencies import get_mongo_db, get_weaviate_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class ServicesStatus(BaseModel):
    mongodb: bool
    weaviate: bool


class HealthResponse(BaseModel):
    status: str
    services: ServicesStatus


@router.get("/health", response_model=HealthResponse)
async def health_check(
    mongo_db: Any = Depends(get_mongo_db),
    weaviate_client: Any = Depends(get_weaviate_client),
) -> HealthResponse:
    """Verify backend connectivity to MongoDB and Weaviate services."""
    mongo_ok = False
    if mongo_db is not None:
        try:
            mongo_db.client.admin.command("ping")
            mongo_ok = True
        except Exception as e:
            logger.debug("MongoDB health ping failed: %s", e)

    weaviate_ok = False
    if weaviate_client is not None:
        try:
            if hasattr(weaviate_client, "is_ready"):
                weaviate_ok = bool(weaviate_client.is_ready())
            elif hasattr(weaviate_client, "is_live"):
                weaviate_ok = bool(weaviate_client.is_live())
            else:
                weaviate_ok = True
        except Exception as e:
            logger.debug("Weaviate health ping failed: %s", e)

    return HealthResponse(
        status="ok",
        services=ServicesStatus(
            mongodb=mongo_ok,
            weaviate=weaviate_ok,
        ),
    )
