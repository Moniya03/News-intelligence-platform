"""Build an immutable local snapshot from the isolated approved corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pymongo import MongoClient

from core.chunking import chunk_article, get_tokenizer

LOG = logging.getLogger(__name__)
CORPUS_DB = "news_intel_corpus_v1"
DATE_FROM = "2026-08-16"
DATE_TO = "2026-11-13"
ADAPTER_LANGS = {
    "abp_en": "en", "abp_hi": "hi", "abp_bn": "bn", "abp_mr": "mr",
    "oneindia_en": "en", "amarujala_hi": "hi", "news18_bn": "bn", "loksatta_mr": "mr",
}
MAX_TOKENS = 256
OVERLAP = 32


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _date_in_window(value: str) -> bool:
    published = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    published = published.astimezone(timezone.utc)
    return datetime(2026, 8, 16, tzinfo=timezone.utc) <= published < datetime(2026, 11, 14, tzinfo=timezone.utc)


def _normal_body(body: str) -> str:
    return re.sub(r"\s+", " ", body).strip().casefold()


def _tokenizer_identity(tokenizer: Any) -> dict[str, str]:
    model = "BAAI/bge-m3"
    if tokenizer.__class__.__name__ == "FallbackTokenizer":
        return {"model": model, "implementation": "fallback-whitespace-v1"}
    commit = getattr(tokenizer, "_commit_hash", None) or getattr(tokenizer, "init_kwargs", {}).get("_commit_hash")
    vocab_file = getattr(tokenizer, "vocab_file", None)
    if not commit and vocab_file:
        for parent in Path(vocab_file).parents:
            if parent.parent.name == "snapshots":
                commit = parent.name
                break
    try:
        transformers_version = version("transformers")
    except PackageNotFoundError:
        transformers_version = "unknown"
    return {
        "model": model,
        "implementation": "transformers.AutoTokenizer",
        "revision": commit or "cached-or-unpinned",
        "transformers_version": transformers_version,
    }


def _read_articles(db, tokenizer: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    source_articles = list(db.articles.find({"adapter_id": {"$in": sorted(ADAPTER_LANGS)}}))
    source_articles.sort(key=lambda item: str(item.get("_id", "")))
    article_payloads: list[dict[str, Any]] = []
    raw_refs: list[dict[str, Any]] = []
    body_groups: dict[str, list[str]] = defaultdict(list)
    langs: Counter[str] = Counter()
    sources: Counter[str] = Counter()

    for article in source_articles:
        article_id = str(article.get("_id", ""))
        body = article.get("body") or ""
        content_hash = article.get("content_hash") or ""
        adapter_id = article.get("adapter_id")
        published_at = article.get("date") or ""
        if not article_id or adapter_id not in ADAPTER_LANGS or article.get("lang") != ADAPTER_LANGS[adapter_id]:
            raise ValueError(f"invalid article identity/language: {article_id}")
        if not article.get("title") or len(body) < 200 or not _date_in_window(published_at):
            raise ValueError(f"article fails pinned selection/quality rules: {article_id}")
        if _sha256(body.encode("utf-8")) != content_hash:
            raise ValueError(f"article body does not match content_hash: {article_id}")
        raw_version_id = article.get("raw_version_id")
        raw = db.raw_article_versions.find_one({"_id": raw_version_id})
        if not raw or raw.get("article_id") != article_id:
            raise ValueError(f"article has missing/mismatched raw version: {article_id}")
        if (raw.get("extracted") or {}).get("content_hash") != content_hash:
            raise ValueError(f"raw version content hash differs: {article_id}")
        canonical_url = article.get("canonical_url") or article.get("url")
        if not canonical_url:
            raise ValueError(f"article has no canonical URL: {article_id}")
        categories = sorted(set(article.get("categories") or []))
        category_mappings = sorted(
            article.get("category_mappings") or [],
            key=lambda mapping: (mapping.get("category", ""), mapping.get("section_url", ""), mapping.get("original_category", "")),
        )
        payload = {
            "article_id": article_id,
            "title": article["title"],
            "body": body,
            "lang": article["lang"],
            "source": article.get("source") or article.get("source_family") or "",
            "source_family": article.get("source_family") or raw.get("source_family") or "",
            "source_adapter": adapter_id,
            "published_at": published_at,
            "original_url": raw.get("original_url") or canonical_url,
            "canonical_url": canonical_url,
            "categories": categories,
            "category": article.get("category") or "unknown",
            "category_mappings": category_mappings,
            "raw_version_id": raw_version_id,
            "raw_html_hash": raw.get("raw_html_hash"),
            "extractor_version": raw.get("extractor_version"),
            "mapping_version": raw.get("mapping_version"),
            "content_hash": content_hash,
        }
        article_payloads.append(payload)
        raw_refs.append({key: payload[key] for key in ("article_id", "raw_version_id", "raw_html_hash", "extractor_version", "mapping_version", "content_hash")})
        body_groups[_sha256(_normal_body(body).encode("utf-8"))].append(article_id)
        langs[payload["lang"]] += 1
        sources[payload["source_adapter"]] += 1

    duplicate_groups = {key: ids for key, ids in body_groups.items() if len(ids) > 1}
    for article in article_payloads:
        body_digest = _sha256(_normal_body(article["body"]).encode("utf-8"))
        article["duplicate_group_id"] = f"exact-{body_digest}" if body_digest in duplicate_groups else None
    duplicate_article_count = sum(len(ids) for ids in duplicate_groups.values())
    articles_bytes = b"".join(_canonical_json(article) for article in article_payloads)
    identity = {
        "corpus_db": CORPUS_DB,
        "selection": {
            "adapters": sorted(ADAPTER_LANGS),
            "languages": sorted(set(ADAPTER_LANGS.values())),
            "published_from": DATE_FROM,
            "published_to": DATE_TO,
            "date_bounds_inclusive": True,
            "minimum_body_characters": 200,
            "deduplication": "exact-normalized-body-sha256-v1; preserve records and group duplicates",
        },
        "nlp": {
            "tokenizer": _tokenizer_identity(tokenizer),
            "max_tokens": MAX_TOKENS,
            "overlap": OVERLAP,
            "title_prefix": True,
            "chunk_schema": "snapshot-chunk-v1",
        },
        "articles_sha256": _sha256(articles_bytes),
    }
    counts = {
        "articles": len(article_payloads),
        "by_language": dict(sorted(langs.items())),
        "by_source_adapter": dict(sorted(sources.items())),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_articles": duplicate_article_count,
    }
    return article_payloads, raw_refs, {"identity": identity, "counts": counts, "articles_bytes": articles_bytes, "duplicate_groups": duplicate_groups}


def build_snapshot(mongo_uri: str = "mongodb://localhost:27017", output_root: str | Path = "data/snapshots", snapshot_id: str | None = None) -> dict[str, Any]:
    """Build and persist a deterministic snapshot; existing IDs are verified, never replaced."""
    tokenizer = get_tokenizer("BAAI/bge-m3")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
        db = client[CORPUS_DB]
        articles, raw_refs, built = _read_articles(db, tokenizer)
        if not articles:
            raise ValueError(f"no qualifying articles found in {CORPUS_DB}")
        identity_bytes = _canonical_json(built["identity"])
        derived_id = "corpus-" + _sha256(identity_bytes)[:20]
        if snapshot_id and snapshot_id != derived_id:
            raise ValueError(f"requested snapshot_id {snapshot_id!r} does not match deterministic ID {derived_id!r}")
        snapshot_id = derived_id

        chunks: list[dict[str, Any]] = []
        for article in articles:
            chunk_rows = chunk_article(
                article_id=article["article_id"], title=article["title"], body=article["body"],
                tokenizer=tokenizer, max_tokens=MAX_TOKENS, overlap=OVERLAP,
                lang=article["lang"], category=article["category"], source=article["source_family"],
            )
            for position, row in enumerate(chunk_rows):
                chunk_id = f"{snapshot_id}:{article['article_id']}:{article['content_hash']}:c{position:03d}"
                chunks.append({
                    "snapshot_id": snapshot_id,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_id,
                    "chunk_position": position,
                    "article_id": article["article_id"],
                    "content_hash": article["content_hash"],
                    "lang": article["lang"],
                    "source": article["source_family"],
                    "source_family": article["source_family"],
                    "source_adapter": article["source_adapter"],
                    "title": article["title"],
                    "published_at": article["published_at"],
                    "original_url": article["original_url"],
                    "canonical_url": article["canonical_url"],
                    "categories": article["categories"],
                    "category": article["category"],
                    "text": row["text"],
                })
        chunks_bytes = b"".join(_canonical_json(chunk) for chunk in chunks)
        manifest = {
            "snapshot_id": snapshot_id,
            **built["identity"],
            "counts": {**built["counts"], "chunks": len(chunks)},
            "raw_version_refs": raw_refs,
            "articles_sha256": built["identity"]["articles_sha256"],
            "chunks_sha256": _sha256(chunks_bytes),
        }
        manifest_bytes = _canonical_json(manifest)
        manifest_hash = _sha256(manifest_bytes)

        folder = Path(output_root) / snapshot_id
        expected_files = {
            "articles.jsonl": built["articles_bytes"],
            "chunks.jsonl": chunks_bytes,
            "manifest.json": manifest_bytes,
        }
        if folder.exists():
            if not folder.is_dir() or any(not (folder / name).is_file() or (folder / name).read_bytes() != content for name, content in expected_files.items()):
                raise ValueError(f"existing snapshot artifacts differ; refusing to replace {folder}")
        else:
            folder.mkdir(parents=True)
            for name, content in expected_files.items():
                (folder / name).write_bytes(content)

        db_manifest = {
            "_id": snapshot_id,
            "snapshot_id": snapshot_id,
            "corpus_db": CORPUS_DB,
            "manifest_sha256": manifest_hash,
            "manifest": manifest,
            "artifacts": {name: f"{folder.as_posix()}/{name}" for name in expected_files},
        }
        existing = db.corpus_snapshots.find_one({"_id": snapshot_id})
        if existing:
            comparable = {key: existing.get(key) for key in db_manifest}
            if comparable != db_manifest:
                raise ValueError(f"existing Mongo snapshot {snapshot_id} differs; refusing replacement")
        else:
            db.corpus_snapshots.insert_one(db_manifest)
        return {"snapshot_id": snapshot_id, "folder": str(folder), "counts": manifest["counts"], "manifest_sha256": manifest_hash}
    finally:
        client.close()


def _self_check() -> None:
    """Small deterministic/frozen-payload check independent of Mongo or production data."""
    from core.chunking import FallbackTokenizer

    fixture = {
        "_id": "fixture-1", "title": "Headline", "body": "word " * 600,
        "lang": "en", "adapter_id": "abp_en", "source_family": "abp",
        "date": "2026-11-01T12:00:00+05:30", "canonical_url": "https://example.test/a",
        "content_hash": _sha256(("word " * 600).encode()), "raw_version_id": "raw-1",
        "categories": ["finance"], "category": "finance",
    }
    class RawCollection:
        def find_one(self, query):
            return {"_id": "raw-1", "article_id": "fixture-1", "raw_html_hash": "raw-hash", "extractor_version": "fixture-v1", "mapping_version": "map-v1", "extracted": {"content_hash": fixture["content_hash"]}}
    class ArticleCollection:
        def find(self, query):
            return [fixture.copy()]
    class FakeDB:
        articles = ArticleCollection()
        raw_article_versions = RawCollection()
    first, _, built_first = _read_articles(FakeDB, FallbackTokenizer())
    repeated, _, built_repeated = _read_articles(FakeDB, FallbackTokenizer())
    assert built_first["identity"]["articles_sha256"] == built_repeated["identity"]["articles_sha256"]
    fixture["body"] = "changed " * 600
    fixture["content_hash"] = _sha256(fixture["body"].encode())
    second, _, built_second = _read_articles(FakeDB, FallbackTokenizer())
    assert first[0]["body"] == "word " * 600 and first[0]["content_hash"] != second[0]["content_hash"]
    assert built_first["identity"]["articles_sha256"] != built_second["identity"]["articles_sha256"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build immutable local corpus snapshot.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--output-root", default="data/snapshots")
    parser.add_argument("--snapshot-id", default=None, help="Optional assertion of deterministic snapshot ID")
    parser.add_argument("--self-check", action="store_true", help="Run isolated deterministic payload assertion")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.self_check:
        _self_check()
        print("snapshot self-check passed")
        return
    result = build_snapshot(args.mongo_uri, args.output_root, args.snapshot_id)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
