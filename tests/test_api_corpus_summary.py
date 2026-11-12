from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from api.routers import summary
from api.routers.summary import SummaryRequest
from api.snapshot_evidence import corpus_summary, load_active_snapshot


class ApiCorpusSummaryTests(unittest.TestCase):
    def test_active_corpus_counts_come_from_verified_snapshot(self):
        manifest, articles = load_active_snapshot()
        with patch("core.snapshot_topics.load_active_topic_run", return_value=None):
            payload = corpus_summary(manifest, articles)
        self.assertEqual(payload["snapshot_id"], "corpus-59b2b589fe3bbdbffdc3")
        self.assertEqual(payload["article_count"], 516)
        self.assertEqual(payload["chunk_count"], 2135)
        self.assertEqual(payload["language_counts"], {"bn": 156, "en": 123, "hi": 116, "mr": 121})
        self.assertEqual(payload["category_counts"]["environment"], 0)
        self.assertEqual(payload["topic_status"], "not_generated")
        self.assertEqual(payload["crawl_status"], "unavailable")
        self.assertIsNone(payload["rejected_count"])
        self.assertEqual(payload["duplicate_count"], 0)

    def test_corpus_topic_counts_come_from_matching_run_artifact(self):
        manifest, articles = load_active_snapshot()
        run = {"run_id": "run", "topic_count": 1, "outlier_count": 1}
        topics = [{"id": -1, "size": 2}, {"id": 0, "size": 3}]
        with patch("core.snapshot_topics.load_active_topic_run", return_value=(run, topics)):
            payload = corpus_summary(manifest, articles)
        self.assertEqual(payload["topic_status"], "generated")
        self.assertEqual(payload["topic_counts"], {"-1": 2, "0": 3})


    def test_summary_request_requires_nonblank_query_and_distinct_article_ids(self):
        valid_id = "a" * 64
        with self.assertRaises(ValidationError):
            SummaryRequest(query="  ", article_ids=[valid_id], snapshot_id="snapshot")
        with self.assertRaises(ValidationError):
            SummaryRequest(query="news", article_ids=[valid_id, valid_id], snapshot_id="snapshot")


    def test_summary_mismatch_is_conflict_and_provider_is_honestly_unavailable(self):
        article = {
            "article_id": "a" * 64,
            "title": "Verified title",
            "body": "server-side evidence only",
            "source_family": "publisher",
            "lang": "en",
            "canonical_url": "https://example.test/story",
        }
        load_snapshot = summary.load_active_snapshot
        summary.load_active_snapshot = lambda: ({"snapshot_id": "active"}, [article])
        try:
            missing = SummaryRequest(query="what happened?", article_ids=["b" * 64], snapshot_id="active")
            with self.assertRaises(HTTPException) as error:
                asyncio.run(summary.summarize(missing))
            self.assertEqual(error.exception.status_code, 404)

            request = SummaryRequest(query="what happened?", article_ids=[article["article_id"]], snapshot_id="stale")
            with self.assertRaises(HTTPException) as error:
                asyncio.run(summary.summarize(request))
            self.assertEqual(error.exception.status_code, 409)

            request.snapshot_id = "active"
            response = asyncio.run(summary.summarize(request))
            self.assertEqual(response.status, "insufficient_evidence")
            self.assertEqual(response.reason, "insufficient_evidence")
            self.assertEqual(response.citations, [])

            article["body"] = "usable source evidence " * 12
            response = asyncio.run(summary.summarize(request))
            self.assertEqual(response.status, "unavailable")
            self.assertIsNone(response.summary)
            self.assertEqual(response.reason, "provider_access_unverified")
            self.assertEqual(response.citations[0].article_id, article["article_id"])
        finally:
            summary.load_active_snapshot = load_snapshot
