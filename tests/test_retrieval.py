"""Unit tests for retrieval modules with mock Weaviate client."""

import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace
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

    def test_unavailable_client_raises_for_every_retrieval_mode(self):
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            retrieve_hybrid(self.query_vec, self.query_text, client=None, top_k=5)
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            retrieve_dense(self.query_vec, client=None, top_k=5)
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            retrieve_bm25(self.query_text, client=None, top_k=5)

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

    def test_query_outages_raise_instead_of_looking_like_empty_results(self):
        cases = (
            ("hybrid", lambda client: retrieve_hybrid(self.query_vec, self.query_text, client, top_k=5)),
            ("near_vector", lambda client: retrieve_dense(self.query_vec, client, top_k=5)),
            ("bm25", lambda client: retrieve_bm25(self.query_text, client, top_k=5)),
        )
        for method, retrieve in cases:
            with self.subTest(method=method):
                query = MagicMock()
                getattr(query, method).side_effect = RuntimeError("transport unavailable")
                collection = SimpleNamespace(query=query)
                client = SimpleNamespace(collections=SimpleNamespace(get=lambda _: collection))
                with self.assertRaisesRegex(RuntimeError, "retrieval failed"):
                    retrieve(client)

    def test_v3_transport_outages_raise_after_v4_fallback(self):
        cases = (
            ("hybrid", lambda client: retrieve_hybrid(self.query_vec, self.query_text, client, top_k=5)),
            ("near_vector", lambda client: retrieve_dense(self.query_vec, client, top_k=5)),
            ("bm25", lambda client: retrieve_bm25(self.query_text, client, top_k=5)),
        )
        for method, retrieve in cases:
            with self.subTest(method=method):
                query_v4 = MagicMock()
                getattr(query_v4, method).side_effect = RuntimeError("v4 unavailable")
                collection = SimpleNamespace(query=query_v4)

                query_v3 = MagicMock()
                query_v3.get.return_value = query_v3
                for builder in ("with_additional", "with_hybrid", "with_near_vector", "with_bm25", "with_limit", "with_where"):
                    getattr(query_v3, builder).return_value = query_v3
                query_v3.do.side_effect = RuntimeError("v3 transport unavailable")
                client = SimpleNamespace(
                    collections=SimpleNamespace(get=lambda _: collection),
                    query=query_v3,
                )
                with self.assertRaisesRegex(RuntimeError, "retrieval failed"):
                    retrieve(client)

    def test_successful_empty_query_remains_empty(self):
        empty_response = SimpleNamespace(objects=[])
        query = MagicMock()
        query.bm25.return_value = empty_response
        collection = SimpleNamespace(query=query)
        client = SimpleNamespace(collections=SimpleNamespace(get=lambda _: collection))
        self.assertEqual(retrieve_bm25(self.query_text, client, top_k=5), [])

    def test_missing_score_metadata_does_not_create_a_rank_score(self):
        response = SimpleNamespace(objects=[SimpleNamespace(properties={"article_id": "a"}, metadata=None)])
        query = SimpleNamespace(bm25=MagicMock(return_value=response))
        client = SimpleNamespace(collections=SimpleNamespace(get=lambda _: SimpleNamespace(query=query)))
        with self.assertRaisesRegex(RuntimeError, "retrieval failed"):
            retrieve_bm25(self.query_text, client, top_k=5)


if __name__ == "__main__":
    unittest.main()
