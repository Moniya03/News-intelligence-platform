"""Tokenizer-based article chunking for Multilingual News Intelligence Platform.

Splits article texts into overlapping token windows using BGE-M3 tokenizer
(or fallback word-based tokenization), prepends title to every chunk,
and updates chunk statistics in MongoDB.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from pymongo import MongoClient

from core.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class FallbackTokenizer:
    """Simple whitespace/word-based fallback tokenizer when HuggingFace is unavailable."""

    def encode(self, text: str, add_special_tokens: bool = False) -> List[str]:
        return text.split()

    def decode(self, tokens: List[str], skip_special_tokens: bool = True) -> str:
        return " ".join(tokens)


def get_tokenizer(model_name: str = "BAAI/bge-m3") -> Any:
    """Load HuggingFace AutoTokenizer for BGE-M3, falling back to local word tokenizer."""
    try:
        from transformers import AutoTokenizer  # type: ignore
        logger.info("Loading AutoTokenizer for '%s'...", model_name)
        return AutoTokenizer.from_pretrained(model_name)
    except Exception as e:
        logger.warning("Could not load HuggingFace tokenizer (%s). Using fallback word tokenizer.", e)
        return FallbackTokenizer()


def chunk_article(
    article_id: str,
    title: str,
    body: str,
    tokenizer: Any,
    max_tokens: int = 256,
    overlap: int = 32,
    lang: str = "en",
    category: str = "general",
    source: str = "news",
) -> List[Dict[str, Any]]:
    """Chunk a single article into overlapping token passages with prepended title.

    Args:
        article_id: Unique article identifier.
        title: Article headline.
        body: Full text content of article.
        tokenizer: Pretrained tokenizer instance with encode/decode methods.
        max_tokens: Maximum tokens per chunk window (default 256).
        overlap: Token overlap between adjacent chunks (default 32).
        lang: Language code.
        category: News category.
        source: Source dataset.

    Returns:
        List of chunk dictionaries with {chunk_id, article_id, chunk_index, text, title, lang, category, source}.
    """
    clean_title = (title or "").strip()
    clean_body = (body or "").strip()

    if not clean_body:
        if clean_title:
            chunk_id = f"{article_id}_c000"
            return [{
                "chunk_id": chunk_id,
                "article_id": article_id,
                "chunk_index": chunk_id,
                "text": clean_title,
                "title": clean_title,
                "lang": lang,
                "category": category,
                "source": source,
            }]
        return []

    try:
        token_ids = tokenizer.encode(clean_body, add_special_tokens=False)
    except Exception:
        token_ids = clean_body.split()

    total_tokens = len(token_ids)
    chunks: List[Dict[str, Any]] = []

    if total_tokens <= max_tokens:
        chunk_text = f"{clean_title} | {clean_body}" if clean_title else clean_body
        chunk_id = f"{article_id}_c000"
        chunks.append({
            "chunk_id": chunk_id,
            "article_id": article_id,
            "chunk_index": chunk_id,
            "text": chunk_text,
            "title": clean_title,
            "lang": lang,
            "category": category,
            "source": source,
        })
        return chunks

    step = max(1, max_tokens - overlap)
    c_idx = 0

    for start_pos in range(0, total_tokens, step):
        end_pos = min(total_tokens, start_pos + max_tokens)
        window = token_ids[start_pos:end_pos]

        try:
            window_text = tokenizer.decode(window, skip_special_tokens=True).strip()
        except Exception:
            window_text = " ".join(window).strip()

        chunk_text = f"{clean_title} | {window_text}" if clean_title else window_text
        chunk_id = f"{article_id}_c{c_idx:03d}"

        chunks.append({
            "chunk_id": chunk_id,
            "article_id": article_id,
            "chunk_index": chunk_id,
            "text": chunk_text,
            "title": clean_title,
            "lang": lang,
            "category": category,
            "source": source,
        })
        c_idx += 1

        if end_pos >= total_tokens:
            break

    return chunks


def chunk_all_articles(
    mongo_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    output_parquet: str | Path = "data/chunks.parquet",
    max_tokens: int = 256,
    overlap: int = 32,
) -> List[Dict[str, Any]]:
    """Read all articles from MongoDB, chunk them, write chunk counts to MongoDB, and export chunks.

    Args:
        mongo_uri: MongoDB connection string.
        db_name: Database name.
        output_parquet: Parquet file destination for chunk records.
        max_tokens: Window token size.
        overlap: Token overlap.

    Returns:
        List of all created chunk dictionaries.
    """
    cfg = get_config()
    mongo_uri = mongo_uri or cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    model_name = cfg.get("models", {}).get("embedder", "BAAI/bge-m3")

    tokenizer = get_tokenizer(model_name)
    all_chunks: List[Dict[str, Any]] = []

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client[db_name]
        coll = db["articles"]
        articles = list(coll.find({}))
    except Exception as e:
        logger.warning("MongoDB unavailable or empty (%s): %s. No articles chunked.", mongo_uri, e)
        return []

    if not articles:
        logger.warning("No articles in collection '%s.articles' to chunk.", db_name)
        return []

    logger.info("Chunking %d articles from MongoDB...", len(articles))

    for art in articles:
        art_id = str(art.get("_id", art.get("article_id", "")))
        title = art.get("title", "")
        body = art.get("body", "")
        lang = art.get("lang", "en")
        cat = art.get("category", "general")
        src = art.get("source", "news")

        chunks = chunk_article(
            article_id=art_id,
            title=title,
            body=body,
            tokenizer=tokenizer,
            max_tokens=max_tokens,
            overlap=overlap,
            lang=lang,
            category=cat,
            source=src,
        )

        all_chunks.extend(chunks)

        # Update article document with chunk count
        coll.update_one({"_id": art_id}, {"$set": {"n_chunks": len(chunks)}})

    # Export chunks to parquet
    out_path = Path(output_parquet)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_chunks)
    df.to_parquet(out_path, index=False)
    logger.info("Saved %d chunks to %s", len(all_chunks), out_path)

    client.close()
    return all_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunk articles from MongoDB.")
    parser.add_argument("--mongo-uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--db", default=None, help="Database name")
    parser.add_argument("--output", default="data/chunks.parquet", help="Output parquet path")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens per chunk")
    parser.add_argument("--overlap", type=int, default=32, help="Token overlap")
    args = parser.parse_args()

    chunk_all_articles(
        mongo_uri=args.mongo_uri,
        db_name=args.db,
        output_parquet=args.output,
        max_tokens=args.max_tokens,
        overlap=args.overlap,
    )
