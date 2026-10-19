"""Unit tests for retrieval modules with mock Weaviate client."""

import unittest
from unittest.mock import MagicMock
import numpy as np

from core.retrieve import retrieve_bm25, retrieve_dense, retrieve_hybrid


class MockWeaviateObject:
    """Mock object mimicking Weaviate v4 query result item."""

    def __init__(self, article_id: str, chunk_index: str, text: str, title: str, lang: str, score: float = 0.88):
        self.properties = {
            "article_id": article_id,
            "chunk_index": chunk_index,
            "text": text,
            "title": title,
            "lang": lang,
            "category": "general",
            "source": "test_feed",
        }
        self.metadata = MagicMock()
        self.metadata.score = score
        self.metadata.certainty = score
        self.metadata.distance = 1.0 - score


class TestRetrieval(unittest.TestCase):
    """Test retrieval functions under various client states."""

    def setUp(self):
        self.query_text = "clean energy solar"
        self.query_vec = np.random.randn(1024).astype(np.float32)

    def test_retrieve_hybrid_none_client(self):
        """When client is None, retrieve_hybrid should return an empty list without error."""
        results = retrieve_hybrid(self.query_vec, self.query_text, client=None, top_k=5)
        self.assertEqual(results, [])

    def test_retrieve_dense_none_client(self):
        """When client is None, retrieve_dense should return an empty list."""
        results = retrieve_dense(self.query_vec, client=None, top_k=5)
        self.assertEqual(results, [])

    def test_retrieve_bm25_none_client(self):
        """When client is None, retrieve_bm25 should return an empty list."""
        results = retrieve_bm25(self.query_text, client=None, top_k=5)
        self.assertEqual(results, [])

    def test_retrieve_hybrid_with_mock_client(self):
        """Test hybrid retrieval structure with mock Weaviate v4 collection response."""
        mock_client = MagicMock()
        mock_collection = MagicMock()

        mock_objects = [
            MockWeaviateObject("en_001", "en_001_c000", "Solar power installation", "Solar Energy", "en", 0.95),
            MockWeaviateObject("hi_002", "hi_002_c000", "सौर ऊर्जा ग्रिड परियोजना", "सौर ऊर्जा", "hi", 0.89),
        ]
        mock_res = MagicMock()
        mock_res.objects = mock_objects

        mock_collection.query.hybrid.return_value = mock_res
        mock_client.collections.get.return_value = mock_collection

        results = retrieve_hybrid(
            self.query_vec,
            self.query_text,
            client=mock_client,
            top_k=2,
            lang_filter=["en", "hi"],
            alpha=0.7,
        )

        self.assertEqual(len(results), 2)
        r0 = results[0]
        self.assertEqual(r0["article_id"], "en_001")
        self.assertEqual(r0["chunk_id"], "en_001_c000")
        self.assertEqual(r0["lang"], "en")
        self.assertAlmostEqual(r0["score"], 0.95)
        self.assertIn("Solar power installation", r0["text"])

        r1 = results[1]
        self.assertEqual(r1["article_id"], "hi_002")
        self.assertEqual(r1["lang"], "hi")


if __name__ == "__main__":
    unittest.main()
