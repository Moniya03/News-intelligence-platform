"""Data ingestion pipeline for Multilingual News Intelligence Platform.

Loads datasets (L3Cube-IndicNews, HinFakeNews, English FakeNews), normalizes
fields, deduplicates via SHA-256 hash, and upserts into MongoDB.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError

from core.config import get_config
from core.dedupe import exact_hash, remove_exact_duplicates

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def normalize_article(raw: Dict[str, Any], lang: str, source: str) -> Dict[str, Any]:
    """Normalize raw dataset records into uniform article structure.

    Args:
        raw: Dictionary containing raw row/record data.
        lang: Language ISO code (en, hi, bn, ta).
        source: Dataset source identifier (e.g. 'l3cube-indicnews', 'hinfakenews').

    Returns:
        Standardized article dict.
    """
    title = str(raw.get("title") or raw.get("headline") or raw.get("heading") or "").strip()
    body = str(raw.get("body") or raw.get("text") or raw.get("news") or raw.get("content") or "").strip()
    category = str(raw.get("category") or raw.get("label") or raw.get("topic") or "general").strip()
    url = raw.get("url") or raw.get("link") or None
    date = raw.get("date") or raw.get("published_date") or None

    return {
        "lang": lang.lower(),
        "title": title,
        "body": body,
        "category": category.lower(),
        "source": source,
        "url": str(url) if url else None,
        "date": str(date) if date else None,
        "cluster_id": None,
        "n_chunks": 0,
    }


def _read_dataframe_safe(path: Path) -> Optional[pd.DataFrame]:
    """Safely read csv, tsv, json, jsonl, or parquet files into a pandas DataFrame."""
    if not path.is_file():
        logger.warning("Dataset file not found: %s", path)
        return None

    suffix = path.suffix.lower()
    try:
        if suffix in [".csv", ".txt"]:
            # Try comma, then tab delimiter
            try:
                df = pd.read_csv(path, on_bad_lines="skip")
            except Exception:
                df = pd.read_csv(path, sep="\t", on_bad_lines="skip")
            return df
        elif suffix == ".tsv":
            return pd.read_csv(path, sep="\t", on_bad_lines="skip")
        elif suffix == ".parquet":
            return pd.read_parquet(path)
        elif suffix in [".json", ".jsonl"]:
            try:
                return pd.read_json(path, lines=True)
            except Exception:
                return pd.read_json(path)
        else:
            logger.warning("Unsupported file extension: %s", suffix)
            return None
    except Exception as e:
        logger.error("Error reading file %s: %s", path, e)
        return None


def load_l3cube_indicnews(path: str | Path, lang: str, max_articles: int = 5000) -> List[Dict[str, Any]]:
    """Load and normalize articles from L3Cube-IndicNews dataset.

    Args:
        path: Path to dataset file or directory.
        lang: Language code (hi, bn, ta, en).
        max_articles: Max records to load (default 5000).

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if file_path.is_dir():
        # Look for matching language file in directory
        candidates = list(file_path.glob(f"*{lang}*.*")) or list(file_path.glob("*.csv"))
        if not candidates:
            logger.warning("No files found for language %s in %s", lang, path)
            return []
        file_path = candidates[0]

    df = _read_dataframe_safe(file_path)
    if df is None or df.empty:
        return []

    articles: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        raw_dict = row.to_dict()
        art = normalize_article(raw_dict, lang=lang, source="l3cube-indicnews")
        if art["body"] or art["title"]:
            articles.append(art)
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles for lang '%s' from %s", len(articles), lang, file_path)
    return articles


def load_hinfakenews(path: str | Path, max_articles: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load and normalize articles from HinFakeNews dataset (Hindi).

    Args:
        path: Path to dataset file or directory.
        max_articles: Optional limit on records.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if file_path.is_dir():
        candidates = list(file_path.glob("*hin*.*")) or list(file_path.glob("*.csv"))
        if not candidates:
            logger.warning("No files found for HinFakeNews in %s", path)
            return []
        file_path = candidates[0]

    df = _read_dataframe_safe(file_path)
    if df is None or df.empty:
        return []

    articles: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        art = normalize_article(row.to_dict(), lang="hi", source="hinfakenews")
        if art["body"] or art["title"]:
            articles.append(art)
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles from HinFakeNews (%s)", len(articles), file_path)
    return articles


def load_english_fakenews(path: str | Path, max_articles: Optional[int] = 5000) -> List[Dict[str, Any]]:
    """Load and normalize articles from English FakeNews dataset.

    Args:
        path: Path to dataset file or directory.
        max_articles: Optional limit on records.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if file_path.is_dir():
        candidates = list(file_path.glob("*en*.*")) or list(file_path.glob("*.csv"))
        if not candidates:
            logger.warning("No files found for English FakeNews in %s", path)
            return []
        file_path = candidates[0]

    df = _read_dataframe_safe(file_path)
    if df is None or df.empty:
        return []

    articles: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        art = normalize_article(row.to_dict(), lang="en", source="english-fakenews")
        if art["body"] or art["title"]:
            articles.append(art)
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles from English FakeNews (%s)", len(articles), file_path)
    return articles


def ingest_all(data_dir: str | Path = "data", mongo_uri: Optional[str] = None, db_name: Optional[str] = None) -> int:
    """Ingest, deduplicate, and upsert all corpus datasets into MongoDB.

    Args:
        data_dir: Path to directory containing raw data.
        mongo_uri: Optional MongoDB URI override.
        db_name: Optional database name override.

    Returns:
        Total number of unique articles upserted.
    """
    cfg = get_config()
    mongo_uri = mongo_uri or cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    data_path = Path(data_dir)

    all_raw_articles: List[Dict[str, Any]] = []

    # 1. Load L3Cube-IndicNews for languages
    for lang in ["hi", "bn", "ta", "en"]:
        l3_path = data_path / "l3cube" / lang
        if not l3_path.exists():
            l3_path = data_path / f"l3cube_{lang}.csv"
        arts = load_l3cube_indicnews(l3_path, lang=lang, max_articles=5000)
        all_raw_articles.extend(arts)

    # 2. Load HinFakeNews
    hin_path = data_path / "hinfakenews"
    if not hin_path.exists():
        hin_path = data_path / "hinfakenews.csv"
    all_raw_articles.extend(load_hinfakenews(hin_path))

    # 3. Load English FakeNews
    en_fake_path = data_path / "english_fakenews"
    if not en_fake_path.exists():
        en_fake_path = data_path / "english_fakenews.csv"
    all_raw_articles.extend(load_english_fakenews(en_fake_path))

    if not all_raw_articles:
        logger.warning("No articles found in data_dir '%s' to ingest.", data_path)
        return 0

    # 4. Remove exact duplicates
    logger.info("Removing exact duplicates from %d raw articles...", len(all_raw_articles))
    unique_articles = remove_exact_duplicates(all_raw_articles)
    logger.info("Retained %d unique articles after exact deduplication.", len(unique_articles))

    # 5. Connect to MongoDB and upsert
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client[db_name]
        coll = db["articles"]
    except Exception as e:
        logger.warning("Could not connect to MongoDB (%s): %s. Skipping DB write.", mongo_uri, e)
        return len(unique_articles)

    bulk_ops: List[UpdateOne] = []
    lang_counters: Dict[str, int] = {}
    total_upserted = 0

    for i, art in enumerate(unique_articles, 1):
        lang = art.get("lang", "en")
        idx = lang_counters.get(lang, 1)
        lang_counters[lang] = idx + 1
        article_id = f"{lang}_{idx:06d}"
        art["_id"] = article_id

        bulk_ops.append(
            UpdateOne({"_id": article_id}, {"$set": art}, upsert=True)
        )

        if len(bulk_ops) >= 500:
            coll.bulk_write(bulk_ops)
            total_upserted += len(bulk_ops)
            print(f"[Ingest] Progress: upserted {total_upserted}/{len(unique_articles)} articles")
            bulk_ops = []

    if bulk_ops:
        coll.bulk_write(bulk_ops)
        total_upserted += len(bulk_ops)
        print(f"[Ingest] Progress: upserted {total_upserted}/{len(unique_articles)} articles")

    logger.info("Successfully ingested %d total articles into MongoDB '%s.articles'", total_upserted, db_name)
    client.close()
    return total_upserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest datasets into MongoDB.")
    parser.add_argument("--data-dir", default="data", help="Directory containing dataset files")
    parser.add_argument("--mongo-uri", default=None, help="MongoDB connection URI")
    parser.add_argument("--db", default=None, help="Database name")
    args = parser.parse_args()

    ingest_all(data_dir=args.data_dir, mongo_uri=args.mongo_uri, db_name=args.db)
