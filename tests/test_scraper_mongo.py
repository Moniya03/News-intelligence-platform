"""Opt-in lifecycle integration test against a dedicated local Mongo database."""

import os
import hashlib
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from pymongo import MongoClient

from scrapers.pipelines import MongoArticlePipeline


class Stats:
    def __init__(self):
        self.values = {"scraper/discovered": 2, "scraper/errors": 0, "scraper/error_urls": []}

    def get_value(self, key, default=None):
        return self.values.get(key, default)


@unittest.skipUnless(os.getenv("MONGO_TEST_URI") and os.getenv("MONGO_TEST_DATABASE"), "set MONGO_TEST_URI and dedicated MONGO_TEST_DATABASE to run Mongo integration")
class TestMongoArticlePipeline(unittest.TestCase):
    def setUp(self):
        self.database_name = os.environ["MONGO_TEST_DATABASE"]
        if not self.database_name.startswith("news_intel_scraper_test_"):
            self.fail("MONGO_TEST_DATABASE must start with news_intel_scraper_test_")
        self.client = MongoClient(os.environ["MONGO_TEST_URI"], serverSelectionTimeoutMS=5000)
        self.client.drop_database(self.database_name)
        self.db = self.client[self.database_name]
        self.stats = Stats()
        self.spider = SimpleNamespace(
            name="abp_en", adapter_id="abp_en", source={"family": "abp", "sections": [], "extractor_version": "extract-v1", "mapping_version": "global-category-v1"},
            max_articles=3,
        )
        self.crawler = SimpleNamespace(spider=self.spider, stats=self.stats)
        self.spider.crawler = self.crawler
        self.pipeline = MongoArticlePipeline(os.environ["MONGO_TEST_URI"], self.database_name)
        self.pipeline.crawler = self.crawler
        self.pipeline.open_spider(self.spider)

    def tearDown(self):
        self.pipeline.client.close()
        self.client.drop_database(self.database_name)
        self.client.close()

    def item(self, *, body, raw_hash, extractor="extract-v1", mapping="global-category-v1", category="finance", original_category="business", section_url="https://news.abplive.com/business", status=200, accepted=True):
        now = datetime.now(timezone.utc)
        return {
            "article_id": "stable-article-id", "adapter_id": "abp_en", "source_family": "abp", "lang": "en", "source": "news.abplive.com",
            "title": "A reported story", "body": body, "date": "2026-11-12T10:00:00+05:30", "published_at": "2026-11-12T10:00:00+05:30",
            "author": "", "category": category, "original_category": original_category, "section_url": section_url,
            "mapping_version": mapping, "canonical_url": "https://news.abplive.com/elections/story-123456", "content_hash": hashlib.sha256(body.encode()).hexdigest(),
            "discovered_from_section": section_url, "original_url": "https://news.abplive.com/elections/story-123456",
            "final_url": "https://news.abplive.com/business/story-123456", "http_status": status, "fetched_at": now,
            "extractor_version": extractor, "raw_html": f"<html>{raw_hash}</html>", "raw_html_hash": raw_hash,
            "accepted": accepted, "rejection_reason": None if accepted else f"http_status_{status}",
        }

    def test_raw_versions_and_failed_fetch_preserve_normalized_article(self):
        body_v1 = "first extracted body " * 20
        first = self.item(body=body_v1, raw_hash="raw-1")
        self.pipeline.process_item(first, self.spider)
        self.pipeline.process_item(first, self.spider)
        self.assertEqual(self.db.raw_article_versions.count_documents({}), 1)
        self.assertEqual(self.db.articles.find_one({"_id": "stable-article-id"})["body"], body_v1)

        self.pipeline.process_item(self.item(body=body_v1, raw_hash="raw-2"), self.spider)
        self.db.articles.update_one({"_id": "stable-article-id"}, {"$set": {"n_chunks": 3, "cluster_id": "cluster-1"}})
        self.pipeline.process_item(self.item(body=body_v1, raw_hash="raw-2", extractor="extract-v2"), self.spider)
        unchanged_article = self.db.articles.find_one({"_id": "stable-article-id"})
        self.assertEqual(unchanged_article["n_chunks"], 3)
        self.assertEqual(unchanged_article["cluster_id"], "cluster-1")
        body_v2 = "second extracted body " * 20
        changed = self.item(body=body_v2, raw_hash="raw-3", extractor="extract-v2", mapping="global-category-v2")
        self.pipeline.process_item(changed, self.spider)
        article_before_failure = self.db.articles.find_one({"_id": "stable-article-id"})
        self.assertEqual(article_before_failure["body"], body_v2)
        self.assertEqual(article_before_failure["mapping_version"], "global-category-v2")
        self.assertEqual(article_before_failure["n_chunks"], 0)
        self.assertIsNone(article_before_failure["cluster_id"])
        self.assertEqual(self.db.raw_article_versions.count_documents({}), 4)

        self.db.articles.update_one({"_id": "stable-article-id"}, {"$set": {"n_chunks": 4, "cluster_id": "cluster-2"}})
        politics_mapping = self.item(body=body_v2, raw_hash="raw-4", extractor="extract-v2", mapping="global-category-v3", category="politics", original_category="elections", section_url="https://news.abplive.com/elections")
        self.pipeline.process_item(politics_mapping, self.spider)
        mapping_changed = self.item(body=body_v2, raw_hash="raw-4", extractor="extract-v2", mapping="global-category-v3")
        self.pipeline.process_item(mapping_changed, self.spider)
        mapping_article = self.db.articles.find_one({"_id": "stable-article-id"})
        self.assertEqual(mapping_article["category"], "politics")
        self.assertEqual(mapping_article["categories"], ["politics", "finance"])
        self.assertEqual(mapping_article["original_category"], "elections")
        self.assertEqual(mapping_article["section_url"], "https://news.abplive.com/elections")
        self.assertEqual(len(mapping_article["category_mappings"]), 2)
        self.assertEqual(mapping_article["body"], body_v2)
        self.assertEqual(mapping_article["n_chunks"], 4)
        self.assertEqual(mapping_article["cluster_id"], "cluster-2")
        self.assertEqual(self.db.raw_article_versions.count_documents({}), 6)
        self.assertEqual(self.db.raw_article_versions.count_documents({"section_url": "https://news.abplive.com/elections"}), 1)
        self.assertEqual(self.db.raw_article_versions.count_documents({"section_url": "https://news.abplive.com/business"}), 5)

        failed = self.item(body="stale body " * 30, raw_hash="raw-404", status=404, accepted=False)
        self.pipeline.process_item(failed, self.spider)
        article_after_failure = self.db.articles.find_one({"_id": "stable-article-id"})
        self.assertEqual(article_after_failure["body"], body_v2)
        self.assertEqual(article_after_failure["raw_version_id"], mapping_article["raw_version_id"])
        self.assertEqual(self.db.raw_article_versions.count_documents({}), 7)

        self.pipeline.close_spider(self.spider)
        self.pipeline.spider_closed(self.spider, "finished")

        # A process restart reuses the stable article/version IDs and doesn't duplicate raw data.
        self.pipeline = MongoArticlePipeline(os.environ["MONGO_TEST_URI"], self.database_name)
        self.pipeline.crawler = self.crawler
        self.pipeline.open_spider(self.spider)
        self.pipeline.process_item(mapping_changed, self.spider)
        self.assertEqual(self.db.raw_article_versions.count_documents({}), 7)
        self.assertEqual(self.db.articles.find_one({"_id": "stable-article-id"})["body"], body_v2)
        self.assertEqual(self.db.articles.find_one({"_id": "stable-article-id"})["n_chunks"], 4)
        self.assertEqual(self.db.articles.find_one({"_id": "stable-article-id"})["categories"], ["politics", "finance"])
        self.pipeline.close_spider(self.spider)
        self.pipeline.spider_closed(self.spider, "finished")
        runs = list(self.db.crawl_runs.find({"adapter_id": "abp_en"}))
        self.assertEqual(len(runs), 2)
        self.assertTrue(all(run["status"] == "finished" for run in runs))
        self.assertEqual(runs[-1]["counts"]["unchanged"], 1)


if __name__ == "__main__":
    unittest.main()
