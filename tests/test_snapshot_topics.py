from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.routers import clusters
from core.snapshot_topics import load_snapshot_topic_inputs


class SnapshotTopicsTests(unittest.TestCase):
    def test_loader_preserves_article_order_and_returns_normalized_vectors(self):
        manifest, articles, article_ids, vectors, provenance = load_snapshot_topic_inputs()
        self.assertEqual(manifest["snapshot_id"], "corpus-59b2b589fe3bbdbffdc3")
        self.assertEqual(article_ids, [article["article_id"] for article in articles])
        self.assertEqual(vectors.shape, (len(article_ids), 1024))
        self.assertTrue((abs((vectors * vectors).sum(axis=1) - 1.0) < 1e-5).all())
        self.assertEqual(provenance["embeddings_sha256"], provenance["embedding"]["embeddings_sha256"])

    def test_topic_routes_keep_empty_unknown_and_real_detail_behavior(self):
        empty = ({"snapshot_id": "snap"}, [], None, [])
        with patch("api.routers.clusters._load_topics", return_value=empty):
            result = asyncio.run(clusters.list_clusters())
            self.assertEqual(result.clusters, [])
            self.assertEqual(result.snapshot_id, "snap")
            with self.assertRaises(HTTPException) as error:
                asyncio.run(clusters.get_cluster_details(42))
            self.assertEqual(error.exception.status_code, 404)

        article = {
            "article_id": "article-1", "title": "Title", "lang": "bn", "source_family": "Publisher",
            "category": "politics", "original_url": "https://example.test/story", "published_at": "2026-11-13T00:00:00Z",
        }
        topic = {
            "id": -1, "label": "Unassigned", "size": 1, "article_ids": ["article-1"],
            "top_terms": [], "lang_counts": {"bn": 1}, "source_counts": {"Publisher": 1},
            "representative_article_ids": ["article-1"],
        }
        populated = ({"snapshot_id": "snap"}, [article], {"run_id": "run", "settings_hash": "hash"}, [topic])
        with patch("api.routers.clusters._load_topics", return_value=populated):
            result = asyncio.run(clusters.get_cluster_details(-1, page=1, limit=20))
        self.assertEqual(result.articles[0].published_at, article["published_at"])
        self.assertEqual(result.articles[0].url, article["original_url"])


if __name__ == "__main__":
    unittest.main()
