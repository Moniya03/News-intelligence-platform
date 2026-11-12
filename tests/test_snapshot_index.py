import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from core.snapshot_index import _properties, _verify_collection, build_snapshot_index
from core.retrieve import retrieve_bm25


class SnapshotIndexTests(unittest.TestCase):
    def test_index_verification_rejects_misaligned_stored_vector(self):
        row = {
            "snapshot_id": "snapshot", "article_id": "article", "content_hash": "hash",
            "chunk_position": 0, "chunk_id": "snapshot:article:hash:c000", "lang": "en",
            "source_family": "publisher", "source_adapter": "publisher_en", "title": "title",
            "published_at": "2026-11-13T10:00:00+05:30", "original_url": "https://example.org/story",
            "canonical_url": "https://example.org/story", "categories": ["politics"],
            "category": "politics", "text": "article body",
        }
        model = {"model": "BAAI/bge-m3", "revision": "revision", "backend": "flagembedding",
                 "device": "cuda", "settings": {"fp16": True}}
        checksums = {"manifest_sha256": "manifest", "chunks_sha256": "chunks", "embeddings_sha256": "vectors"}
        properties = _properties(row, model, checksums)
        obj = SimpleNamespace(properties=properties, vector=np.zeros(1024, dtype=np.float32))
        collection = SimpleNamespace(
            aggregate=SimpleNamespace(over_all=lambda **_: SimpleNamespace(total_count=1)),
            query=SimpleNamespace(fetch_objects=lambda **_: SimpleNamespace(objects=[obj])),
        )

        with self.assertRaisesRegex(RuntimeError, "vector readback mismatch"):
            _verify_collection(collection, [row], model, checksums, np.ones((1, 1024), dtype=np.float32))

    def test_active_snapshot_search_uses_collection_and_returns_provenance(self):
        props = {
            "chunk_id": "snapshot:article:hash:c000", "article_id": "article", "text": "body",
            "title": "title", "lang": "hi", "category": "politics", "categories": ["politics"],
            "source_family": "publisher", "source_adapter": "publisher_hi", "snapshot_id": "snapshot",
            "content_hash": "hash", "chunk_position": 0, "original_url": "https://example.org/story",
            "canonical_url": "https://example.org/story", "published_at": "2026-11-13T10:00:00+05:30",
        }
        result = SimpleNamespace(objects=[SimpleNamespace(properties=props, metadata=SimpleNamespace(score=1.0))])
        collection = SimpleNamespace(query=SimpleNamespace(bm25=MagicMock(return_value=result)))
        client = SimpleNamespace(collections=SimpleNamespace(get=MagicMock(return_value=collection)))
        with patch("core.retrieve.get_config", return_value={"active_snapshot": {"index_collection": "SnapshotIndex"}}):
            hits = retrieve_bm25("query", client)

        client.collections.get.assert_called_once_with("SnapshotIndex")
        self.assertEqual(hits[0]["url"], "https://example.org/story")
        self.assertEqual(hits[0]["published_at"], props["published_at"])
        self.assertEqual(hits[0]["snapshot_id"], "snapshot")
        self.assertEqual(hits[0]["source_adapter"], "publisher_hi")

    def test_chunk_checksum_failure_does_not_activate_or_change_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot_id = "snapshot-test"
            snapshot_dir = root / "snapshots" / snapshot_id
            snapshot_dir.mkdir(parents=True)
            row = {
                "snapshot_id": snapshot_id,
                "article_id": "article-1",
                "content_hash": "content-sha",
                "chunk_position": 0,
                "chunk_id": f"{snapshot_id}:article-1:content-sha:c000",
                "chunk_index": f"{snapshot_id}:article-1:content-sha:c000",
                "lang": "en",
                "source_family": "publisher",
                "source_adapter": "publisher_en",
                "title": "A real title",
                "published_at": "2026-11-13T10:00:00+05:30",
                "original_url": "https://example.org/article",
                "canonical_url": "https://example.org/article",
                "categories": ["politics"],
                "category": "politics",
                "text": "An article body with enough content to index.",
            }
            chunks = (json.dumps(row) + "\n").encode()
            (snapshot_dir / "chunks.jsonl").write_bytes(chunks)
            manifest = {"snapshot_id": snapshot_id, "corpus_db": "news_intel_corpus_v1",
                        "chunks_sha256": hashlib.sha256(b"different bytes").hexdigest(),
                        "counts": {"chunks": 1}}
            (snapshot_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            config = root / "default.yaml"
            original = 'mongo:\n  db: "news_intel"\n\nactive_snapshot: null\n'
            config.write_text(original, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "chunks checksum mismatch"):
                build_snapshot_index(snapshot_id, activate=True, snapshots_dir=root / "snapshots",
                                     config_path=config)

            self.assertEqual(config.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
