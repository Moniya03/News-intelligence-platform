"""Weaviate schema creation and vector loading for Multilingual News Intelligence Platform.

Manages Weaviate NewsChunk collection/class, properties, BM25 indexing,
and batch loading of chunk texts and dense vectors.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import weaviate

from core.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CLASS_NAME = "NewsChunk"


def get_weaviate_client(host: Optional[str] = None, port: Optional[int] = None) -> Any:
    """Connect to Weaviate instance using configuration.

    Args:
        host: Weaviate host address (default from config/default.yaml).
        port: Weaviate HTTP port (default from config/default.yaml).

    Returns:
        weaviate.WeaviateClient or None if unreachable.
    """
    cfg = get_config()
    w_cfg = cfg.get("weaviate", {})
    resolved_host = host or w_cfg.get("host", "localhost")
    resolved_port = port or int(w_cfg.get("port", 8080))

    try:
        if hasattr(weaviate, "connect_to_local"):
            client = weaviate.connect_to_local(
                host=resolved_host,
                port=resolved_port,
                grpc_port=50051,
            )
            if client.is_ready():
                logger.info("Connected to Weaviate (v4) at %s:%d", resolved_host, resolved_port)
                return client
            logger.warning("Weaviate is not ready at %s:%d", resolved_host, resolved_port)
            return client
        else:
            # Fallback for weaviate v3 syntax if present
            url = f"http://{resolved_host}:{resolved_port}"
            client = weaviate.Client(url=url)  # type: ignore
            return client
    except Exception as e:
        logger.warning("Failed to connect to Weaviate at %s:%s: %s", resolved_host, resolved_port, e)
        return None


def create_weaviate_schema(client: Any) -> bool:
    """Create the NewsChunk collection / class in Weaviate.

    Properties:
        article_id (text)
        chunk_index (text)
        text (text) - indexed with BM25
        title (text)
        lang (text)
        category (text)
        source (text)

    Args:
        client: Active Weaviate client.

    Returns:
        bool: True if created or exists, False otherwise.
    """
    if client is None:
        logger.warning("Cannot create schema: Weaviate client is None.")
        return False

    # Check v4 API first
    if hasattr(client, "collections"):
        try:
            import weaviate.classes.config as wvc

            if client.collections.exists(CLASS_NAME):
                logger.info("Collection '%s' already exists in Weaviate.", CLASS_NAME)
                return True

            client.collections.create(
                name=CLASS_NAME,
                vectorizer_config=wvc.Configure.Vectorizer.none(),
                properties=[
                    wvc.Property(name="article_id", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="chunk_index", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="text", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="title", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="lang", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="category", data_type=wvc.DataType.TEXT),
                    wvc.Property(name="source", data_type=wvc.DataType.TEXT),
                ],
            )
            logger.info("Created collection '%s' in Weaviate (v4 API).", CLASS_NAME)
            return True
        except Exception as e:
            logger.error("Error creating Weaviate collection (v4): %s", e)

    # Check v3 schema API fallback
    if hasattr(client, "schema"):
        try:
            schema = client.schema.get()
            existing_classes = [c.get("class") for c in schema.get("classes", [])]
            if CLASS_NAME in existing_classes:
                logger.info("Class '%s' already exists in Weaviate (v3).", CLASS_NAME)
                return True

            class_obj = {
                "class": CLASS_NAME,
                "description": "Multilingual news chunk with dense vector and BM25 index",
                "vectorizer": "none",
                "properties": [
                    {"name": "article_id", "dataType": ["string"]},
                    {"name": "chunk_index", "dataType": ["string"]},
                    {"name": "text", "dataType": ["text"]},
                    {"name": "title", "dataType": ["text"]},
                    {"name": "lang", "dataType": ["string"]},
                    {"name": "category", "dataType": ["string"]},
                    {"name": "source", "dataType": ["string"]},
                ],
            }
            client.schema.create_class(class_obj)
            logger.info("Created class '%s' in Weaviate (v3 API).", CLASS_NAME)
            return True
        except Exception as e:
            logger.error("Error creating Weaviate class (v3): %s", e)

    return False


def load_vectors(
    client: Any,
    chunks_parquet: str | Path = "data/chunks.parquet",
    vectors_npy: str | Path = "data/vectors.npy",
    batch_size: int = 100,
) -> int:
    """Batch import chunks and corresponding dense vectors into Weaviate.

    Args:
        client: Active Weaviate client.
        chunks_parquet: Path to chunks parquet file.
        vectors_npy: Path to dense vectors npy file.
        batch_size: Batch size for loading.

    Returns:
        int: Number of imported objects.
    """
    if client is None:
        logger.warning("Weaviate client is None. Skipping vector load.")
        return 0

    c_path = Path(chunks_parquet)
    v_path = Path(vectors_npy)

    if not c_path.is_file():
        logger.warning("Chunks parquet not found: %s", c_path)
        return 0
    if not v_path.is_file():
        logger.warning("Vectors file not found: %s", v_path)
        return 0

    df = pd.read_parquet(c_path)
    vectors = np.load(v_path)

    if len(df) != len(vectors):
        logger.warning("Length mismatch: %d chunks vs %d vectors", len(df), len(vectors))

    n_items = min(len(df), len(vectors))
    logger.info("Loading %d items into Weaviate collection '%s'...", n_items, CLASS_NAME)

    # Check v4 API
    if hasattr(client, "collections"):
        try:
            collection = client.collections.get(CLASS_NAME)
            with collection.batch.dynamic() as batch:
                for i in range(n_items):
                    row = df.iloc[i]
                    properties = {
                        "article_id": str(row.get("article_id", "")),
                        "chunk_index": str(row.get("chunk_index", row.get("chunk_id", ""))),
                        "text": str(row.get("text", "")),
                        "title": str(row.get("title", "")),
                        "lang": str(row.get("lang", "")),
                        "category": str(row.get("category", "")),
                        "source": str(row.get("source", "")),
                    }
                    vec = vectors[i].tolist() if isinstance(vectors[i], np.ndarray) else vectors[i]
                    batch.add_object(properties=properties, vector=vec)

            logger.info("Successfully imported %d items into Weaviate (v4).", n_items)
            return n_items
        except Exception as e:
            logger.error("Failed batch loading with v4 API: %s", e)

    # Check v3 API fallback
    if hasattr(client, "batch"):
        try:
            client.batch.configure(batch_size=batch_size)
            with client.batch as batch:
                for i in range(n_items):
                    row = df.iloc[i]
                    properties = {
                        "article_id": str(row.get("article_id", "")),
                        "chunk_index": str(row.get("chunk_index", row.get("chunk_id", ""))),
                        "text": str(row.get("text", "")),
                        "title": str(row.get("title", "")),
                        "lang": str(row.get("lang", "")),
                        "category": str(row.get("category", "")),
                        "source": str(row.get("source", "")),
                    }
                    vec = vectors[i].tolist() if isinstance(vectors[i], np.ndarray) else vectors[i]
                    batch.add_data_object(
                        data_object=properties,
                        class_name=CLASS_NAME,
                        vector=vec,
                    )
            logger.info("Successfully imported %d items into Weaviate (v3).", n_items)
            return n_items
        except Exception as e:
            logger.error("Failed batch loading with v3 API: %s", e)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Weaviate index and load vectors.")
    parser.add_argument("--chunks", default="data/chunks.parquet", help="Path to chunks parquet")
    parser.add_argument("--vectors", default="data/vectors.npy", help="Path to vectors npy")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch import size")
    args = parser.parse_args()

    c = get_weaviate_client()
    if c is not None:
        create_weaviate_schema(c)
        load_vectors(c, chunks_parquet=args.chunks, vectors_npy=args.vectors, batch_size=args.batch_size)
    else:
        logger.warning("Could not connect to Weaviate. Skipping schema creation and indexing.")
