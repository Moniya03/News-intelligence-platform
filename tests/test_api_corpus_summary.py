from __future__ import annotations

import unittest
from unittest.mock import patch

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
