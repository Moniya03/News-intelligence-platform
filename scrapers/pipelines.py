from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pymongo import MongoClient
from scrapy import signals

from scrapers.sources import CATEGORY_ORDER


class MongoArticlePipeline:
    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls(crawler.settings.get("MONGO_URI", "mongodb://localhost:27017"), crawler.settings.get("MONGO_DATABASE", "news_intel"))
        pipeline.crawler = crawler
        crawler.signals.connect(pipeline.spider_closed, signal=signals.spider_closed)
        return pipeline

    def __init__(self, uri, database):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[database]

    def open_spider(self, *args):
        spider = args[0] if args else self.crawler.spider
        self.client.admin.command("ping")
        self.run_id = hashlib.sha256(f"{spider.name}:{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:24]
        self.started_at = datetime.now(timezone.utc)
        self.counts = {"discovered": 0, "fetched": 0, "accepted": 0, "rejected": 0, "unchanged": 0, "errors": 0}
        self.db.crawl_runs.insert_one({"_id": self.run_id, "adapter_id": spider.adapter_id, "source_family": spider.source["family"], "sections": spider.source["sections"], "max_articles": spider.max_articles, "extractor_version": spider.source["extractor_version"], "mapping_version": spider.source.get("mapping_version"), "started_at": self.started_at, "status": "running", "counts": self.counts.copy(), "errors": []})

    def process_item(self, item, *args):
        self.counts["fetched"] += 1
        self.counts["accepted" if item["accepted"] else "rejected"] += 1
        if item["http_status"] != 200:
            self.counts["errors"] += 1
        category_mappings = item.get("category_mappings") or [{key: item.get(key) for key in ("category", "original_category", "section_url", "mapping_version")}]
        context_key = "|".join(sorted(":".join(str(mapping.get(key) or "") for key in ("category", "original_category", "section_url", "mapping_version")) for mapping in category_mappings))
        raw_id = hashlib.sha256(f"{item['article_id']}:{item['raw_html_hash']}:{item['extractor_version']}:{item['mapping_version']}:{context_key}".encode()).hexdigest()
        raw = {key: item[key] for key in ("article_id", "adapter_id", "source_family", "discovered_from_section", "section_url", "original_category", "category", "category_mappings", "mapping_version", "original_url", "final_url", "canonical_url", "http_status", "fetched_at", "published_at", "extractor_version", "raw_html", "raw_html_hash") if key in item}
        raw["extracted"] = {key: item.get(key) for key in ("lang", "source", "title", "body", "date", "author", "category", "original_category", "section_url", "category_mappings", "mapping_version", "content_hash", "accepted", "rejection_reason")}
        raw["_id"] = raw_id
        result = self.db.raw_article_versions.update_one({"_id": raw_id}, {"$setOnInsert": raw}, upsert=True)
        if result.upserted_id is None:
            self.counts["unchanged"] = self.counts.get("unchanged", 0) + 1
        if item["accepted"]:
            existing = self.db.articles.find_one({"_id": item["article_id"]}, {"content_hash": 1, "mapping_version": 1, "category_mappings": 1})
            current_mappings = []
            if existing and existing.get("mapping_version") == item["mapping_version"]:
                current_mappings.extend(existing.get("category_mappings", []))
            current_mappings.extend(category_mappings)
            unique_mappings = {}
            for mapping in current_mappings:
                if mapping.get("mapping_version") == item["mapping_version"] and mapping.get("category") in CATEGORY_ORDER:
                    key = tuple(str(mapping.get(k) or "") for k in ("category", "original_category", "section_url", "mapping_version"))
                    unique_mappings[key] = {k: mapping.get(k) for k in ("category", "original_category", "section_url", "mapping_version")}
            mappings = sorted(unique_mappings.values(), key=lambda mapping: (CATEGORY_ORDER.index(mapping["category"]), mapping.get("section_url") or "", mapping.get("original_category") or ""))
            categories = [category for category in CATEGORY_ORDER if any(mapping["category"] == category for mapping in mappings)]
            primary = mappings[0] if mappings else {"category": item["category"], "original_category": item.get("original_category"), "section_url": item.get("section_url"), "mapping_version": item["mapping_version"]}
            article = {key: item[key] for key in ("article_id", "title", "body", "lang", "source", "source_family", "adapter_id", "canonical_url", "date", "author", "content_hash")}
            article.update({"category": primary["category"], "original_category": primary.get("original_category"), "section_url": primary.get("section_url"), "mapping_version": primary.get("mapping_version"), "categories": categories, "category_mappings": mappings})
            article.update({"url": item["canonical_url"], "raw_version_id": raw_id, "last_seen_at": item["fetched_at"]})
            if existing is None:
                self.db.articles.update_one({"_id": item["article_id"]}, {"$set": article, "$setOnInsert": {"first_seen_at": item["fetched_at"], "cluster_id": None, "n_chunks": 0}}, upsert=True)
            else:
                if existing.get("content_hash") != item["content_hash"]:
                    article.update({"cluster_id": None, "n_chunks": 0})
                self.db.articles.update_one({"_id": item["article_id"]}, {"$set": article}, upsert=True)
        self._save_counts()
        return item

    def _save_counts(self):
        self.db.crawl_runs.update_one({"_id": self.run_id}, {"$set": {"counts": self.counts.copy()}})

    def close_spider(self, *args):
        if not hasattr(self, "run_id"):
            return
        spider = args[0] if args else self.crawler.spider
        self.counts["discovered"] = spider.crawler.stats.get_value("scraper/discovered", 0)
        self.counts["errors"] += spider.crawler.stats.get_value("scraper/errors", 0)
        errors = spider.crawler.stats.get_value("scraper/error_urls", [])

        self.db.crawl_runs.update_one({"_id": self.run_id}, {"$set": {"counts": self.counts.copy(), "errors": errors}})

    def spider_closed(self, spider, reason):
        try:
            if hasattr(self, "run_id"):
                self.db.crawl_runs.update_one({"_id": self.run_id}, {"$set": {"ended_at": datetime.now(timezone.utc), "status": "finished" if reason == "finished" else "stopped", "close_reason": reason, "counts": self.counts.copy()}})
        finally:
            self.client.close()
