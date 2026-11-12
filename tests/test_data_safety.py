import unittest
from unittest.mock import patch

from core.cluster import _assert_cluster_store_empty, _persist_cluster_run
from core.ingest import _assert_legacy_ingest_target, _assert_no_article_id_collisions, ingest_all


class FakeCollection:
    def __init__(self, document=None):
        self.document = document
        self.queries = []

    def find_one(self, query, projection=None):
        self.queries.append(query)
        return self.document


class FakeWritableCollection:
    def __init__(self, documents=None, fail_on_update=None, concurrent_assignment=None):
        self.documents = documents or {}
        self.fail_on_update = fail_on_update
        self.concurrent_assignment = concurrent_assignment

    def insert_one(self, document):
        self.documents[document["_id"]] = dict(document)

    def update_one(self, query, update):
        article_id = query["_id"]
        if article_id == self.fail_on_update and "$set" in update:
            if self.concurrent_assignment:
                target_id, cluster_id = self.concurrent_assignment
                self.documents[target_id]["cluster_id"] = cluster_id
            raise OSError("simulated write failure")
        document = self.documents.setdefault(article_id, {"_id": article_id})
        if "cluster_id" in query and document.get("cluster_id") != query["cluster_id"]:
            return
        document.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            document.pop(field, None)

    def delete_many(self, query):
        for cluster_id in query["_id"]["$in"]:
            self.documents.pop(cluster_id, None)


class DataSafetyTests(unittest.TestCase):
    def test_ingest_refuses_sequential_ids_that_already_exist(self):
        collection = FakeCollection({"_id": "en_000001"})
        with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
            _assert_no_article_id_collisions(collection, ["en_000001", "en_000002"])

    def test_ingest_allows_non_colliding_ids(self):
        collection = FakeCollection()
        _assert_no_article_id_collisions(collection, ["en_000001"])
        self.assertEqual(collection.queries[0]["_id"]["$in"], ["en_000001"])

    def test_legacy_ingest_requires_explicit_separate_database(self):
        with self.assertRaisesRegex(RuntimeError, "separate isolated database"):
            _assert_legacy_ingest_target(None, "news_intel")
        with self.assertRaisesRegex(RuntimeError, "separate isolated database"):
            _assert_legacy_ingest_target("news_intel", "news_intel")
        self.assertEqual(_assert_legacy_ingest_target("legacy_eval", "news_intel"), "legacy_eval")

    def test_ingest_entrypoint_rejects_live_database_before_io(self):
        with patch("core.ingest.get_config", return_value={"mongo": {"db": "news_intel"}}), patch(
            "core.ingest.MongoClient"
        ) as mongo_client:
            with self.assertRaisesRegex(RuntimeError, "separate isolated database"):
                ingest_all(data_dir="missing", db_name="news_intel")
        mongo_client.assert_not_called()

    def test_clustering_refuses_to_replace_existing_records_or_assignments(self):
        with self.subTest(reason="existing cluster documents"):
            with self.assertRaisesRegex(RuntimeError, "refusing to replace"):
                _assert_cluster_store_empty(FakeCollection(), FakeCollection({"_id": 1}))
        with self.subTest(reason="existing article assignments"):
            with self.assertRaisesRegex(RuntimeError, "refusing to replace"):
                _assert_cluster_store_empty(FakeCollection({"cluster_id": 1}), FakeCollection())

    def test_clustering_allows_an_empty_store(self):
        _assert_cluster_store_empty(FakeCollection(), FakeCollection())

    def test_cluster_write_failure_rolls_back_this_run(self):
        articles = FakeWritableCollection(
            {"en_1": {"_id": "en_1"}, "hi_1": {"_id": "hi_1"}},
            fail_on_update="hi_1",
        )
        clusters = FakeWritableCollection()
        with self.assertRaisesRegex(RuntimeError, "writes were rolled back"):
            _persist_cluster_run(
                articles,
                clusters,
                ["en_1", "hi_1"],
                [0, 1],
                [{"id": 0, "label": "topic 0"}, {"id": 1, "label": "topic 1"}],
            )
        self.assertEqual(clusters.documents, {})
        self.assertNotIn("cluster_id", articles.documents["en_1"])
        self.assertNotIn("cluster_id", articles.documents["hi_1"])

    def test_cluster_rollback_preserves_concurrent_assignment(self):
        articles = FakeWritableCollection(
            {"en_1": {"_id": "en_1"}, "hi_1": {"_id": "hi_1"}},
            fail_on_update="hi_1",
            concurrent_assignment=("en_1", 99),
        )
        clusters = FakeWritableCollection()
        with self.assertRaisesRegex(RuntimeError, "writes were rolled back"):
            _persist_cluster_run(
                articles,
                clusters,
                ["en_1", "hi_1"],
                [0, 1],
                [{"id": 0, "label": "topic 0"}, {"id": 1, "label": "topic 1"}],
            )
        self.assertEqual(articles.documents["en_1"]["cluster_id"], 99)
        self.assertEqual(clusters.documents, {})


if __name__ == "__main__":
    unittest.main()
