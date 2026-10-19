"""FastAPI Main Application for Multilingual News Intelligence Platform.

Configures lifespan startup and shutdown hooks, CORS middleware,
and exposes endpoints for search, chat/RAG, topic clusters, and health probes.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from api.routers import chat, clusters, health, search
from core.config import get_config
from core.embed import get_embed_model
from core.index import get_weaviate_client
from core.rag import get_gemini_client
from core.rerank import get_rerank_model

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("api.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: initialize models and DB clients on startup; cleanup on shutdown."""
    logger.info("Initializing backend services and models...")
    cfg = get_config()

    # 1. Initialize BGE-M3 EmbedModel & Reranker
    try:
        app.state.embed_model = get_embed_model()
        logger.info("EmbedModel initialized.")
    except Exception as e:
        logger.error("Failed to initialize EmbedModel: %s", e)
        app.state.embed_model = None

    try:
        app.state.rerank_model = get_rerank_model()
        logger.info("RerankModel initialized.")
    except Exception as e:
        logger.error("Failed to initialize RerankModel: %s", e)
        app.state.rerank_model = None

    # 2. Connect to MongoDB
    mongo_uri = cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")
    db_name = cfg.get("mongo", {}).get("db", "news_intel")
    try:
        mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        mongo_client.admin.command("ping")
        app.state.mongo_client = mongo_client
        app.state.mongo_db = mongo_client[db_name]
        logger.info("Connected to MongoDB at %s (db: %s)", mongo_uri, db_name)
    except Exception as e:
        logger.warning("Could not connect to MongoDB (%s): %s", mongo_uri, e)
        app.state.mongo_client = None
        app.state.mongo_db = None

    # 3. Connect to Weaviate
    try:
        weaviate_client = get_weaviate_client()
        app.state.weaviate_client = weaviate_client
        logger.info("Weaviate client initialized.")
    except Exception as e:
        logger.warning("Could not connect to Weaviate: %s", e)
        app.state.weaviate_client = None

    # 4. Initialize Gemini client
    try:
        app.state.gemini_client = get_gemini_client()
        if app.state.gemini_client is not None:
            logger.info("Gemini Flash client initialized.")
    except Exception as e:
        logger.warning("Could not initialize Gemini client: %s", e)
        app.state.gemini_client = None

    logger.info("Backend initialization complete.")
    yield

    # Shutdown
    logger.info("Shutting down backend services...")
    if getattr(app.state, "mongo_client", None) is not None:
        app.state.mongo_client.close()
        logger.info("Closed MongoDB client connection.")
    if getattr(app.state, "weaviate_client", None) is not None:
        try:
            if hasattr(app.state.weaviate_client, "close"):
                app.state.weaviate_client.close()
        except Exception:
            pass
        logger.info("Closed Weaviate connection.")


app = FastAPI(
    title="Multilingual News Intelligence API",
    description="Cross-lingual news search, RAG synthesis, and topic clustering for English, Hindi, Bengali, and Tamil.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers under /api
app.include_router(chat.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(clusters.router, prefix="/api")
app.include_router(health.router, prefix="/api")


@app.get("/")
async def root():
    """Root health and welcome message."""
    return {
        "name": "Multilingual News Intelligence Platform API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }
