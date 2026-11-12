"""Focused tests for honest API and model-unavailable behavior."""

import asyncio
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.routers import chat, clusters, search
from core.embed import EmbedModel
from core.rerank import RerankModel


class _Cursor(list):
    def skip(self, count):
        return self

    def limit(self, count):
        return self


class _Collection:
    def __init__(self, docs=(), detail=None):
        self.docs = list(docs)
        self.detail = detail

    def find(self, query):
        return _Cursor(self.docs)

    def find_one(self, query):
        return self.detail

    def count_documents(self, query):
        return len(self.docs)


class _Database(dict):
    pass


class TestSearchTruthfulness(unittest.TestCase):
    def test_actual_no_match_is_empty_success(self):
        query = type("Query", (), {"bm25": lambda self, **kwargs: type("Response", (), {"objects": []})()})()
        collection = type("Collection", (), {"query": query})()
        client = type("Client", (), {"collections": type("Collections", (), {"get": lambda self, name: collection})()})()
        result = asyncio.run(search.search_articles(
            search.SearchRequest(query="no match", mode="bm25"),
            embed_model=None,
            weaviate_client=client,
        ))
        self.assertEqual(result.results, [])

    def test_unavailable_index_is_503(self):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(search.search_articles(
                search.SearchRequest(query="query", mode="bm25"),
                embed_model=None,
                weaviate_client=None,
            ))
        self.assertEqual(caught.exception.status_code, 503)

    @patch("api.routers.search.retrieve_bm25", side_effect=RuntimeError("offline"))
    def test_retrieval_failure_is_503(self, _):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(search.search_articles(
                search.SearchRequest(query="query", mode="bm25"),
                embed_model=None,
                weaviate_client=object(),
            ))
        self.assertEqual(caught.exception.status_code, 503)


class TestClusterTruthfulness(unittest.TestCase):
    def test_empty_collection_is_empty_success(self):
        db = _Database(clusters=_Collection())
        self.assertEqual(asyncio.run(clusters.list_clusters(db)).clusters, [])

    def test_unknown_cluster_is_404(self):
        db = _Database(clusters=_Collection(detail=None), articles=_Collection())
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(clusters.get_cluster_details(99, page=1, limit=20, mongo_db=db))
        self.assertEqual(caught.exception.status_code, 404)

    def test_unavailable_store_is_503(self):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(clusters.list_clusters(None))
        self.assertEqual(caught.exception.status_code, 503)


class TestChatTruthfulness(unittest.TestCase):
    class _Embedder:
        def embed_query(self, query):
            return [0.1]

    class _Reranker:
        def rerank(self, query, candidates, top_k):
            return candidates[:top_k]

    def test_no_retrieved_evidence_returns_empty_answer(self):
        with patch("api.routers.chat.retrieve_hybrid", return_value=[]):
            result = asyncio.run(chat.chat_endpoint(
                chat.ChatRequest(query="unknown"), self._Embedder(), self._Reranker(), object(), None
            ))
        self.assertEqual(result.answer, "Not found in the indexed articles.")
        self.assertEqual(result.citations, [])

    @patch("api.routers.chat.retrieve_hybrid", return_value=[{"article_id": "1", "chunk_id": "1", "text": "evidence", "score": 1.0}])
    @patch("api.routers.chat.generate_answer", side_effect=RuntimeError("provider missing"))
    def test_missing_answer_provider_is_503(self, _generate, _retrieve):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(chat.chat_endpoint(
                chat.ChatRequest(query="question"), self._Embedder(), self._Reranker(), object(), None
            ))
        self.assertEqual(caught.exception.status_code, 503)

    @patch("api.routers.chat.retrieve_hybrid", side_effect=RuntimeError("index unavailable"))
    def test_retrieval_outage_is_503(self, _retrieve):
        with self.assertRaises(HTTPException) as caught:
            asyncio.run(chat.chat_endpoint(
                chat.ChatRequest(query="question"), self._Embedder(), self._Reranker(), object(), None
            ))
        self.assertEqual(caught.exception.status_code, 503)


class TestModelFallbackRemoval(unittest.TestCase):
    def test_embedder_does_not_emit_synthetic_vectors(self):
        model = EmbedModel.__new__(EmbedModel)
        model.backend = "unavailable"
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            model.embed_texts(["a real query"])

    def test_failed_reranker_preserves_retrieval_results_and_scores(self):
        model = RerankModel.__new__(RerankModel)
        model.backend = "unavailable"
        model._model = None
        candidates = [
            {"article_id": "1", "chunk_id": "1", "text": "first passage unique", "score": 0.2},
            {"article_id": "2", "chunk_id": "2", "text": "second passage distinct", "score": 0.8},
        ]
        result = model.rerank("query", candidates)
        self.assertEqual([item["article_id"] for item in result], ["1", "2"])
        self.assertEqual([item["score"] for item in result], [0.2, 0.8])

    def test_reranker_inference_error_preserves_retrieval_results_and_scores(self):
        class FailedModel:
            def predict(self, pairs):
                raise RuntimeError("inference failed")

        model = RerankModel.__new__(RerankModel)
        model.backend = "cross_encoder"
        model._model = FailedModel()
        candidates = [
            {"article_id": "1", "chunk_id": "1", "text": "first passage unique", "score": 0.2},
            {"article_id": "2", "chunk_id": "2", "text": "second passage distinct", "score": 0.8},
        ]
        result = model.rerank("query", candidates)
        self.assertEqual([item["article_id"] for item in result], ["1", "2"])
        self.assertEqual([item["score"] for item in result], [0.2, 0.8])

    def test_reranker_short_score_vector_preserves_every_candidate(self):
        class ShortScores:
            def predict(self, pairs):
                return [0.99]

        model = RerankModel.__new__(RerankModel)
        model.backend = "cross_encoder"
        model._model = ShortScores()
        candidates = [
            {"article_id": "1", "chunk_id": "1", "text": "first passage unique", "score": 0.2},
            {"article_id": "2", "chunk_id": "2", "text": "second passage distinct", "score": 0.8},
        ]
        result = model.rerank("query", candidates)
        self.assertEqual([item["article_id"] for item in result], ["1", "2"])
        self.assertEqual([item["score"] for item in result], [0.2, 0.8])


if __name__ == "__main__":
    unittest.main()
