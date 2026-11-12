"""Verified access to the configured immutable article snapshot."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import get_config
from core.snapshot_index import collection_name, load_snapshot

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = ("politics", "finance", "health", "science_technology", "environment", "sports")


def load_active_snapshot(config: dict[str, Any] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cfg = config or get_config()
    active = cfg.get("active_snapshot") or {}
    snapshot_id = active.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id.startswith("corpus-"):
        raise ValueError("active snapshot is not configured")
    snapshot_dir = ROOT / "data" / "snapshots" / snapshot_id
    configured_manifest = (ROOT / str(active.get("manifest", ""))).resolve()
    if configured_manifest != (snapshot_dir / "manifest.json").resolve():
        raise ValueError("active snapshot manifest path does not match snapshot id")

    manifest, _, manifest_bytes, _ = load_snapshot(snapshot_id, snapshot_dir.parent)
    identity = {key: manifest[key] for key in ("corpus_db", "selection", "nlp", "articles_sha256")}
    identity_bytes = (json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    expected_id = "corpus-" + hashlib.sha256(identity_bytes).hexdigest()[:20]
    expected_manifest_hash = active.get("manifest_sha256")
    if expected_id != snapshot_id or (expected_manifest_hash and hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_hash):
        raise ValueError("active snapshot identity or manifest checksum mismatch")
    if active.get("index_collection") != collection_name(snapshot_id):
        raise ValueError("active snapshot collection does not match snapshot id")

    articles_bytes = (snapshot_dir / "articles.jsonl").read_bytes()
    if hashlib.sha256(articles_bytes).hexdigest() != manifest.get("articles_sha256"):
        raise ValueError("snapshot article checksum mismatch")
    articles = [json.loads(line) for line in articles_bytes.splitlines() if line]
    expected_count = manifest.get("counts", {}).get("articles")
    article_ids: set[str] = set()
    for article in articles:
        article_id = article.get("article_id")
        body = article.get("body")
        if not isinstance(article_id, str) or not article_id or article_id in article_ids or not isinstance(body, str):
            raise ValueError("snapshot article identity/body is invalid")
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != article.get("content_hash"):
            raise ValueError(f"snapshot article body checksum mismatch: {article_id}")
        article_ids.add(article_id)
    if len(articles) != expected_count:
        raise ValueError("snapshot article count mismatch")
    return manifest, articles


def corpus_summary(manifest: dict[str, Any], articles: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or get_config()
    counts = manifest["counts"]
    languages = Counter(article["lang"] for article in articles)
    adapters = sorted({article["source_adapter"] for article in articles})
    categories = sorted(CATEGORIES)
    matrix: dict[str, dict[str, int]] = {adapter: dict.fromkeys(categories, 0) for adapter in adapters}
    category_counts: Counter[str] = Counter()
    for article in articles:
        adapter = article["source_adapter"]
        for category in set(article.get("categories", [])) & set(CATEGORIES):
            category_counts[category] += 1
            matrix[adapter][category] += 1
    dates = []
    for article in articles:
        published = datetime.fromisoformat(str(article["published_at"]).replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        dates.append(published.astimezone(timezone.utc))
    collection_name = (cfg.get("active_snapshot") or {}).get("index_collection")
    topic_counts: dict[str, int] | None = None
    topic_status = "not_generated"
    try:
        from core.snapshot_topics import load_active_topic_run

        topic_run = load_active_topic_run(manifest["snapshot_id"], [article["article_id"] for article in articles], cfg)
        if topic_run is not None:
            run, topics = topic_run
            topic_counts = {str(topic["id"]): int(topic["size"]) for topic in topics}
            topic_status = "generated"
    except Exception:
        topic_status = "unavailable"
    return {
        "snapshot_id": manifest["snapshot_id"],
        "article_count": len(articles),
        "chunk_count": counts["chunks"],
        "language_counts": dict(sorted(languages.items())),
        "source_counts": dict(sorted(Counter(article["source_family"] for article in articles).items())),
        "source_adapter_counts": dict(sorted(Counter(article["source_adapter"] for article in articles).items())),
        "category_counts": {category: category_counts[category] for category in categories},
        "coverage": {"adapter_category_counts": matrix},
        "published_from": min(dates).isoformat().replace("+00:00", "Z"),
        "published_to": max(dates).isoformat().replace("+00:00", "Z"),
        "last_successful_crawl_at": None,
        "collection_status": "configured" if collection_name else "unavailable",
        "collection_name": collection_name,
        "topic_counts": topic_counts,
        "topic_status": topic_status,
        "rejected_count": None,
        "crawl_status": "unavailable",
        "duplicate_count": counts.get("duplicate_articles"),
    }
