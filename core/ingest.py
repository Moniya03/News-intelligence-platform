"""Data ingestion pipeline for Multilingual News Intelligence Platform.

Loads datasets (IndicNLP Bengali, Tamil News, HinFakeNews, English FakeNews/TrueNews),
normalizes fields, deduplicates via SHA-256 hash, and upserts into MongoDB.
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
        source: Dataset source identifier (e.g. 'indicnlp-bengali', 'hinfakenews').

    Returns:
        Standardized article dict.
    """
    title = str(raw.get("title") or raw.get("TITLE") or raw.get("headline") or raw.get("heading") or "").strip()
    body = str(raw.get("body") or raw.get("CONTENT") or raw.get("text") or raw.get("news") or raw.get("content") or "").strip()
    category = str(raw.get("category") or raw.get("Category") or raw.get("label") or raw.get("subject") or raw.get("topic") or "general").strip()
    url = raw.get("url") or raw.get("URL") or raw.get("link") or raw.get("NewsInEnglish") or None
    date = raw.get("date") or raw.get("published_date") or None

    # Fallback: if body is missing but title exists, use title as body
    if not body and title:
        body = title
    elif not title and body:
        title = body[:100]

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
    """Safely read csv, tsv, xlsx, json, jsonl, or parquet files into a pandas DataFrame."""
    if not path.is_file():
        logger.warning("Dataset file not found: %s", path)
        return None

    suffix = path.suffix.lower()
    try:
        if suffix in [".csv", ".txt"]:
            try:
                df = pd.read_csv(path, on_bad_lines="skip")
            except Exception:
                df = pd.read_csv(path, sep="\t", on_bad_lines="skip")
            return df
        elif suffix == ".tsv":
            return pd.read_csv(path, sep="\t", on_bad_lines="skip")
        elif suffix in [".xlsx", ".xls"]:
            return pd.read_excel(path)
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


def load_bengali_news(path: str | Path, max_articles: int = 5000) -> List[Dict[str, Any]]:
    """Load and normalize Bengali news articles from JSON/TXT files.

    Args:
        path: Directory containing Bengali news files.
        max_articles: Max records to load.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if not file_path.exists():
        logger.warning("Bengali path does not exist: %s", path)
        return []

    files = list(file_path.rglob("*.txt")) + list(file_path.rglob("*.json"))
    if not files:
        logger.warning("No txt or json files found in %s", path)
        return []

    articles: List[Dict[str, Any]] = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            raw_list = data.get("articles", []) if isinstance(data, dict) else data
            for item in raw_list:
                art = normalize_article(item, lang="bn", source="indicnlp-bengali")
                if art["body"] or art["title"]:
                    articles.append(art)
                if max_articles and len(articles) >= max_articles:
                    break
        except Exception as e:
            logger.warning("Failed to parse Bengali file %s: %s", fp, e)

        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles for lang 'bn' from %s", len(articles), path)
    return articles


def load_tamil_news(path: str | Path, max_articles: int = 5000) -> List[Dict[str, Any]]:
    """Load and normalize Tamil news articles from CSV files.

    Args:
        path: Path or directory for Tamil news.
        max_articles: Max records to load.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if file_path.is_dir():
        candidates = list(file_path.glob("tamil_news_*.csv")) or list(file_path.glob("*.csv"))
    else:
        candidates = [file_path] if file_path.exists() else []

    if not candidates:
        logger.warning("No Tamil CSV files found in %s", path)
        return []

    articles: List[Dict[str, Any]] = []
    for fp in candidates:
        df = _read_dataframe_safe(fp)
        if df is None or df.empty:
            continue
        for _, row in df.iterrows():
            raw_dict = row.to_dict()
            headline = raw_dict.get("NewsInTamil", "")
            raw_dict["title"] = headline
            raw_dict["body"] = headline
            art = normalize_article(raw_dict, lang="ta", source="indicnlp-tamil")
            if art["body"] or art["title"]:
                articles.append(art)
            if max_articles and len(articles) >= max_articles:
                break
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles for lang 'ta' from %s", len(articles), path)
    return articles


def load_hinfakenews(path: str | Path, max_articles: Optional[int] = 5000) -> List[Dict[str, Any]]:
    """Load and normalize articles from HinFakeNews dataset (Hindi).

    Args:
        path: Path to dataset file or directory.
        max_articles: Optional limit on records.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    if file_path.is_dir():
        candidates = list(file_path.glob("*hin*.*")) or list(file_path.glob("*.xlsx")) or list(file_path.glob("*.csv"))
        if not candidates:
            logger.warning("No files found for HinFakeNews in %s", path)
            return []
        file_path = candidates[0]

    df = _read_dataframe_safe(file_path)
    if df is None or df.empty:
        return []

    articles: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        raw = row.to_dict()
        art = normalize_article(raw, lang="hi", source="hinfakenews")
        if art["body"] or art["title"]:
            articles.append(art)
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles from HinFakeNews (%s)", len(articles), file_path)
    return articles


def load_english_fakenews(path: str | Path, max_articles: Optional[int] = 5000) -> List[Dict[str, Any]]:
    """Load and normalize articles from English Fake/True News dataset.

    Args:
        path: Path to dataset file or directory.
        max_articles: Optional limit on records.

    Returns:
        List of normalized article dicts.
    """
    file_path = Path(path)
    candidates: List[Path] = []
    if file_path.is_dir():
        candidates = list(file_path.glob("*.csv"))
    elif file_path.exists():
        candidates = [file_path]

    if not candidates:
        logger.warning("No files found for English News in %s", path)
        return []

    articles: List[Dict[str, Any]] = []
    # If multiple CSVs (e.g. True.csv and Fake.csv), split quota evenly
    quota_per_file = max_articles // len(candidates) if max_articles else None

    for fp in candidates:
        df = _read_dataframe_safe(fp)
        if df is None or df.empty:
            continue
        file_loaded = 0
        for _, row in df.iterrows():
            raw = row.to_dict()
            art = normalize_article(raw, lang="en", source="english-news")
            if art["body"] or art["title"]:
                articles.append(art)
                file_loaded += 1
            if quota_per_file and file_loaded >= quota_per_file:
                break
        if max_articles and len(articles) >= max_articles:
            break

    logger.info("Loaded %d articles from English News (%s)", len(articles), file_path)
    return articles


def load_l3cube_indicnews(path: str | Path, lang: str, max_articles: int = 5000) -> List[Dict[str, Any]]:
    """Load and normalize articles from L3Cube-IndicNews dataset if available."""
    file_path = Path(path)
    if file_path.is_dir():
        candidates = list(file_path.glob(f"*{lang}*.*")) or list(file_path.glob("*.csv"))
        if not candidates:
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


def ingest_all(
    data_dir: str | Path = "data",
    mongo_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    target_per_lang: int = 5000,
) -> int:
    """Ingest, deduplicate, and upsert all corpus datasets into MongoDB.

    Args:
        data_dir: Path to data directory (checks both data_dir and data_dir/raw).
        mongo_uri: Optional MongoDB URI override.
        db_name: Optional database name override.
        target_per_lang: Target number of articles per language (default 5000).

    Returns:
        Total number of unique articles upserted.
    """
    cfg = get_config()
    mongo_uri = mongo_uri or cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    base_data = Path(data_dir)
    raw_data = base_data / "raw" if (base_data / "raw").exists() else base_data

    all_raw_articles: List[Dict[str, Any]] = []

    # 1. Hindi (HinFakeNews)
    hin_dirs = [raw_data / "hinfakenews", base_data / "hinfakenews", raw_data / "hinfakenews.xlsx", base_data / "hinfakenews.xlsx"]
    for hp in hin_dirs:
        if hp.exists():
            all_raw_articles.extend(load_hinfakenews(hp, max_articles=target_per_lang))
            break

    # 2. Bengali
    bn_dirs = [raw_data / "bn", base_data / "bn"]
    for bp in bn_dirs:
        if bp.exists():
            all_raw_articles.extend(load_bengali_news(bp, max_articles=target_per_lang))
            break

    # 3. Tamil
    ta_dirs = [raw_data / "ta", base_data / "ta"]
    for tp in ta_dirs:
        if tp.exists():
            all_raw_articles.extend(load_tamil_news(tp, max_articles=target_per_lang))
            break

    # 4. English
    en_dirs = [raw_data / "en_fake", base_data / "en_fake", raw_data / "english_fakenews", base_data / "english_fakenews"]
    for ep in en_dirs:
        if ep.exists():
            all_raw_articles.extend(load_english_fakenews(ep, max_articles=target_per_lang))
            break

    # 5. Check L3Cube paths for any languages
    for lang in ["hi", "bn", "ta", "en"]:
        l3_path = raw_data / "l3cube" / lang
        if l3_path.exists():
            all_raw_articles.extend(load_l3cube_indicnews(l3_path, lang=lang, max_articles=target_per_lang))

    if not all_raw_articles:
        logger.warning("No articles found in data directory '%s' to ingest.", base_data)
        return 0

    # 6. Remove exact duplicates
    logger.info("Removing exact duplicates from %d raw articles...", len(all_raw_articles))
    unique_articles = remove_exact_duplicates(all_raw_articles)
    logger.info("Retained %d unique articles after exact deduplication.", len(unique_articles))

    # 7. Connect to MongoDB and upsert
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        db = client[db_name]
        coll = db["articles"]
    except Exception as e:
        logger.error("Could not connect to MongoDB (%s): %s. Aborting DB write.", mongo_uri, e)
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
    parser.add_argument("--target", type=int, default=5000, help="Target articles per language")
    args = parser.parse_args()

    ingest_all(data_dir=args.data_dir, mongo_uri=args.mongo_uri, db_name=args.db, target_per_lang=args.target)
