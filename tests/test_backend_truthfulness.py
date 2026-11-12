"""Focused tests for honest API and model-unavailable behavior."""

import asyncio
import unittest
from unittest.mock import patch
from types import SimpleNamespace

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
    @staticmethod
    def _request(client, embed=None, reranker=None):
        return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            weaviate_client=client, embed_model=embed, rerank_model=reranker
        )))

    def test_actual_no_match_is_empty_success(self):
        query = type("Query", (), {"bm25": lambda self, **kwargs: type("Response", (), {"objects": []})()})()
        collection = type("Collection", (), {"query": query})()
        client = type("Client", (), {"collections": type("Collections", (), {"get": lambda self, name: collection})()})()
        with patch("api.routers.search.get_config", return_value={"active_snapshot": {"snapshot_id": "snap"}}):
            result = asyncio.run(search.search_articles(
                search.SearchRequest(query="no match", mode="bm25"), self._request(client)
            ))
        self.assertEqual(result.results, [])
        self.assertEqual(result.metadata.snapshot_id, "snap")
        self.assertEqual(result.metadata.executed_mode, "bm25")

    def test_bm25_keeps_best_chunk_per_article_and_snapshot_provenance(self):
        props = lambda chunk, text, score, snapshot="snap": {
            "article_id": "article-1" if chunk != "other" else "article-2",
            "chunk_id": chunk, "text": text, "title": chunk, "lang": "en", "source": "publisher",
            "category": "news", "original_url": f"https://news.test/{chunk}",
            "published_at": "2026-01-02T03:04:05Z", "snapshot_id": snapshot,
        }
        objs = [
            SimpleNamespace(properties=props("first", "first excerpt", 0.9), metadata=SimpleNamespace(score=0.9)),
            SimpleNamespace(properties=props("second", "duplicate article chunk", 0.8), metadata=SimpleNamespace(score=0.8)),
            SimpleNamespace(properties=props("other", "another article", 0.7), metadata=SimpleNamespace(score=0.7)),
        ]
        query = SimpleNamespace(bm25=lambda **kwargs: SimpleNamespace(objects=objs))
        collection = SimpleNamespace(query=query)
        client = SimpleNamespace(collections=SimpleNamespace(get=lambda _: collection))
        request = self._request(client, embed=SimpleNamespace(embed_query=lambda _: self.fail("BM25 must not embed")))
        with patch("api.routers.search.get_config", return_value={"active_snapshot": {"snapshot_id": "snap"}}):
            result = asyncio.run(search.search_articles(search.SearchRequest(query="story", mode="bm25", top_k=2), request))
        self.assertEqual([item.article_id for item in result.results], ["article-1", "article-2"])
        self.assertEqual(result.results[0].url, "https://news.test/first")
        self.assertEqual(result.results[0].published_at, "2026-01-02T03:04:05Z")
        self.assertEqual(result.results[0].snapshot_id, "snap")
        self.assertEqual(result.metadata.reranker_status, "disabled")

    def test_mixed_snapshot_results_are_unavailable(self):
        obj = SimpleNamespace(
            properties={"article_id": "a", "text": "body", "snapshot_id": "old"},
            metadata=SimpleNamespace(score=1.0),
        )
        query = SimpleNamespace(bm25=lambda **kwargs: SimpleNamespace(objects=[obj]))
        client = SimpleNamespace(collections=SimpleNamespace(get=lambda _: SimpleNamespace(query=query)))
        with patch("api.routers.search.get_config", return_value={"active_snapshot": {"snapshot_id": "snap"}}):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(search.search_articles(search.SearchRequest(query="story", mode="bm25"), self._request(client)))
        self.assertEqual(caught.exception.status_code, 503)

    def test_unavailable_index_is_503(self):
        with patch("api.routers.search.get_weaviate_client", return_value=None):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(search.search_articles(
                    search.SearchRequest(query="query", mode="bm25"), self._request(None)
                ))
        self.assertEqual(caught.exception.status_code, 503)

    @patch("api.routers.search.retrieve_bm25", side_effect=RuntimeError("offline"))
    def test_retrieval_failure_is_503(self, _):
        with self.assertRaises(HTTPException) as caught:
            with patch("api.routers.search.get_config", return_value={"active_snapshot": {"snapshot_id": "snap"}}):
                asyncio.run(search.search_articles(
                    search.SearchRequest(query="query", mode="bm25"), self._request(object())
                ))
        self.assertEqual(caught.exception.status_code, 503)


class TestClusterTruthfulness(unittest.TestCase):
    def test_empty_collection_is_empty_success(self):
        empty_snapshot = ({"snapshot_id": "snap"}, [], None, [])
        with patch("api.routers.clusters._load_topics", return_value=empty_snapshot):
            result = asyncio.run(clusters.list_clusters())
        self.assertEqual(result.clusters, [])
        self.assertEqual(result.snapshot_id, "snap")

    def test_unknown_cluster_is_404(self):
        no_run = ({"snapshot_id": "snap"}, [], None, [])
        with patch("api.routers.clusters._load_topics", return_value=no_run):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(clusters.get_cluster_details(99, page=1, limit=20))
        self.assertEqual(caught.exception.status_code, 404)

    def test_unavailable_store_is_503(self):
        with patch("api.routers.clusters.load_active_snapshot", side_effect=RuntimeError("snapshot unavailable")):
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(clusters.list_clusters())
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

    def test_search_rerank_status_keeps_retrieval_score_while_legacy_rerank_returns_model_score(self):
        class ScoredModel:
            def predict(self, pairs):
                return [0.9, 0.1]

        model = RerankModel.__new__(RerankModel)
        model.backend = "cross_encoder"
        model._model = ScoredModel()
        candidates = [
            {"article_id": "1", "text": "unique first passage", "score": 0.2},
            {"article_id": "2", "text": "unique second passage", "score": 0.8},
        ]
        ranked, status = model.rerank_with_status("query", candidates)
        self.assertEqual(status, "applied")
        self.assertEqual(ranked[0]["article_id"], "1")
        self.assertEqual(ranked[0]["score"], 0.2)
        self.assertEqual(ranked[0]["rerank_score"], 0.9)
        legacy = model.rerank("query", candidates)
        self.assertEqual(legacy[0]["score"], 0.9)


if __name__ == "__main__":
    unittest.main()
