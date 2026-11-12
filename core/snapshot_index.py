"""Build and verify a snapshot-scoped Weaviate index before activation."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from core.config import get_config
from core.embed import get_embed_model
from core.index import get_weaviate_client

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
PROPERTIES = [
    "chunk_id", "chunk_index", "snapshot_id", "article_id", "content_hash", "chunk_position",
    "original_url", "canonical_url", "published_at", "lang", "source", "source_family",
    "source_adapter", "title", "categories", "category", "text", "embedding_model",
    "embedding_revision", "embedding_backend", "embedding_device", "embedding_settings",
    "manifest_sha256", "chunks_sha256", "embeddings_sha256",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collection_name(snapshot_id: str) -> str:
    suffix = hashlib.sha256(snapshot_id.encode("utf-8")).hexdigest()[:40]
    return f"NewsChunkSnapshot{suffix}"


def load_snapshot(snapshot_id: str, snapshots_dir: Path = ROOT / "data" / "snapshots") -> tuple[dict, list[dict], bytes, bytes]:
    folder = snapshots_dir / snapshot_id
    manifest_bytes = (folder / "manifest.json").read_bytes()
    chunks_bytes = (folder / "chunks.jsonl").read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("snapshot_id") != snapshot_id:
        raise ValueError("snapshot id does not match manifest")
    if manifest.get("chunks_sha256") != _sha256(chunks_bytes):
        raise ValueError("snapshot chunks checksum mismatch")
    rows = [json.loads(line) for line in chunks_bytes.splitlines() if line]
    expected_count = manifest.get("counts", {}).get("chunks")
    if expected_count != len(rows) or not rows:
        raise ValueError(f"snapshot chunk count mismatch: manifest={expected_count}, file={len(rows)}")

    seen_ids: set[str] = set()
    closed_articles: set[str] = set()
    current_article = None
    expected_positions: dict[str, int] = {}
    for row in rows:
        required = ("snapshot_id", "article_id", "content_hash", "chunk_position", "chunk_id", "lang",
                    "source_family", "source_adapter", "title", "published_at", "original_url",
                    "canonical_url", "categories", "category", "text")
        if any(row.get(key) is None or row.get(key) == "" for key in required):
            raise ValueError("snapshot chunk is missing required provenance or text")
        if row["snapshot_id"] != snapshot_id:
            raise ValueError("chunk snapshot id mismatch")
        article_id = str(row["article_id"])
        if current_article != article_id:
            if current_article is not None:
                closed_articles.add(current_article)
            if article_id in closed_articles:
                raise ValueError("snapshot chunks are not grouped in article order")
            current_article = article_id
        position = row["chunk_position"]
        if not isinstance(position, int) or position != expected_positions.get(article_id, 0):
            raise ValueError(f"invalid chunk position for article {article_id}")
        expected_positions[article_id] = position + 1
        expected_id = f"{snapshot_id}:{article_id}:{row['content_hash']}:c{position:03d}"
        if row["chunk_id"] != expected_id or row.get("chunk_index", expected_id) != expected_id:
            raise ValueError("chunk id does not match snapshot, article version, and position")
        if row["chunk_id"] in seen_ids:
            raise ValueError("duplicate chunk id in snapshot")
        seen_ids.add(row["chunk_id"])
    return manifest, rows, manifest_bytes, chunks_bytes


def _model_metadata(model: Any, cfg: dict, batch_size: int) -> dict:
    if getattr(model, "backend", None) != "flagembedding":
        raise RuntimeError("BGE-M3 FlagEmbedding backend is unavailable")
    cache = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
    revisions = list(cache.glob("*"))
    if not revisions:
        raise RuntimeError("cached BGE-M3 revision is unavailable")
    # EmbedModel loads the first cached BGE-M3 revision; retain the same resolved revision here.
    revision = revisions[0].name
    import torch

    runtime_device = "cuda" if torch.cuda.is_available() and model.device == "cuda" else "cpu"
    settings = {
        "fp16": bool(model.fp16 and runtime_device == "cuda"),
        "device": runtime_device,
        "batch_size": batch_size,
        "max_length": 512,
        "return_dense": True,
        "return_sparse": False,
        "return_colbert_vecs": False,
        "backend": model.backend,
    }
    if runtime_device == "cuda":
        settings["gpu"] = torch.cuda.get_device_name(0)
    return {"model": cfg.get("models", {}).get("embedder", "BAAI/bge-m3"), "revision": revision,
            "backend": model.backend, "device": runtime_device, "settings": settings}


def _embeddings(snapshot_dir: Path, rows: list[dict], metadata: dict, chunks_checksum: str, model: Any) -> tuple[np.ndarray, str]:
    vectors_path = snapshot_dir / "embeddings.npy"
    metadata_path = snapshot_dir / "embeddings.json"
    expected = {"snapshot_id": rows[0]["snapshot_id"], "chunks_sha256": chunks_checksum, **metadata}
    if vectors_path.is_file() and metadata_path.is_file():
        try:
            cache = json.loads(metadata_path.read_text(encoding="utf-8"))
            if all(cache.get(key) == value for key, value in expected.items()) and _file_sha256(vectors_path) == cache.get("embeddings_sha256"):
                vectors = np.load(vectors_path, mmap_mode="r")
                if vectors.shape == (len(rows), 1024):
                    return vectors, cache["embeddings_sha256"]
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            pass

    vectors = np.empty((len(rows), 1024), dtype=np.float32)
    batch_size = metadata["settings"]["batch_size"]
    for start in range(0, len(rows), batch_size):
        end = min(start + batch_size, len(rows))
        embedded = model.embed_texts([row["text"] for row in rows[start:end]], batch_size=batch_size)
        if embedded.shape != (end - start, 1024):
            raise RuntimeError(f"embedding count/dimension mismatch at chunks {start}:{end}")
        vectors[start:end] = embedded
        if end % 128 == 0 or end == len(rows):
            logger.info("Embedded %d/%d snapshot chunks", end, len(rows))

    if vectors.shape[0] != len(rows):
        raise RuntimeError("embedding and chunk counts differ")
    with tempfile.NamedTemporaryFile(dir=snapshot_dir, prefix="embeddings-", suffix=".npy", delete=False) as tmp:
        temp_vectors = Path(tmp.name)
    try:
        np.save(temp_vectors, vectors)
        checksum = _file_sha256(temp_vectors)
        os.replace(temp_vectors, vectors_path)
        metadata_path.write_text(json.dumps({**expected, "embeddings_sha256": checksum}, sort_keys=True) + "\n", encoding="utf-8")
        return vectors, checksum
    finally:
        temp_vectors.unlink(missing_ok=True)


def _properties(row: dict, model_meta: dict, checksums: dict) -> dict:
    return {
        "chunk_id": row["chunk_id"], "chunk_index": row["chunk_id"], "snapshot_id": row["snapshot_id"],
        "article_id": row["article_id"], "content_hash": row["content_hash"], "chunk_position": row["chunk_position"],
        "original_url": row["original_url"], "canonical_url": row["canonical_url"], "published_at": str(row["published_at"]),
        "lang": row["lang"], "source": row["source_family"], "source_family": row["source_family"],
        "source_adapter": row["source_adapter"], "title": row["title"], "categories": row["categories"],
        "category": row["category"], "text": row["text"], "embedding_model": model_meta["model"],
        "embedding_revision": model_meta["revision"], "embedding_backend": model_meta["backend"],
        "embedding_device": model_meta["device"],
        "embedding_settings": json.dumps(model_meta["settings"], sort_keys=True, separators=(",", ":")),
        "manifest_sha256": checksums["manifest_sha256"], "chunks_sha256": checksums["chunks_sha256"],
        "embeddings_sha256": checksums["embeddings_sha256"],
    }


def _ensure_collection(client: Any, name: str) -> Any:
    if not hasattr(client, "collections"):
        raise RuntimeError("snapshot indexing requires the Weaviate v4 client")
    collections = client.collections
    if not collections.exists(name):
        import weaviate.classes.config as wvc

        collections.create(
            name=name,
            vectorizer_config=wvc.Configure.Vectorizer.none(),
            properties=[
                wvc.Property(name="chunk_id", data_type=wvc.DataType.TEXT),
                wvc.Property(name="chunk_index", data_type=wvc.DataType.TEXT),
                wvc.Property(name="snapshot_id", data_type=wvc.DataType.TEXT),
                wvc.Property(name="article_id", data_type=wvc.DataType.TEXT),
                wvc.Property(name="content_hash", data_type=wvc.DataType.TEXT),
                wvc.Property(name="chunk_position", data_type=wvc.DataType.INT),
                *[wvc.Property(name=key, data_type=wvc.DataType.TEXT) for key in (
                    "original_url", "canonical_url", "published_at", "lang", "source", "source_family",
                    "source_adapter", "title", "category", "text", "embedding_model", "embedding_revision",
                    "embedding_backend", "embedding_device", "embedding_settings", "manifest_sha256",
                    "chunks_sha256", "embeddings_sha256")],
                wvc.Property(name="categories", data_type=wvc.DataType.TEXT_ARRAY),
            ],
        )
    return collections.get(name)


def _verify_collection(collection: Any, rows: list[dict], model_meta: dict, checksums: dict,
                       vectors: np.ndarray) -> None:
    actual_count = collection.aggregate.over_all(total_count=True).total_count
    if actual_count != len(rows):
        raise RuntimeError(f"Weaviate count mismatch: expected {len(rows)}, found {actual_count}")
    row_by_id = {row["chunk_id"]: i for i, row in enumerate(rows)}
    seen: set[str] = set()
    for offset in range(0, len(rows), 200):
        page = collection.query.fetch_objects(
            limit=200, offset=offset, return_properties=PROPERTIES, include_vector=True,
        )
        for obj in page.objects:
            chunk_id = obj.properties.get("chunk_id")
            row_index = row_by_id.get(chunk_id)
            if row_index is None or chunk_id in seen:
                raise RuntimeError(f"Weaviate readback contains unexpected chunk {chunk_id}")
            row = rows[row_index]
            expected = _properties(row, model_meta, checksums)
            if any(obj.properties.get(key) != value for key, value in expected.items()):
                raise RuntimeError(f"Weaviate provenance readback mismatch for chunk {chunk_id}")
            stored_vector = obj.vector
            if isinstance(stored_vector, dict):
                stored_vector = stored_vector.get("default", next(iter(stored_vector.values())))
            if not np.array_equal(np.asarray(stored_vector, dtype=np.float32), vectors[row_index]):
                raise RuntimeError(f"Weaviate vector readback mismatch for chunk {chunk_id}")
            seen.add(chunk_id)
    if len(seen) != len(rows):
        raise RuntimeError(f"Weaviate readback mismatch: expected {len(rows)}, found {len(seen)} unique chunks")


def _insert_missing(collection: Any, rows: list[dict], vectors: np.ndarray,
                    model_meta: dict, checksums: dict) -> None:
    result = collection.query.fetch_objects(limit=len(rows), return_properties=PROPERTIES)
    expected_by_id = {row["chunk_id"]: row for row in rows}
    existing_ids: set[str] = set()
    for obj in result.objects:
        chunk_id = obj.properties.get("chunk_id")
        row = expected_by_id.get(chunk_id)
        if row is None or chunk_id in existing_ids:
            raise RuntimeError(f"Existing snapshot collection contains unexpected chunk {chunk_id}")
        expected = _properties(row, model_meta, checksums)
        if any(obj.properties.get(key) != value for key, value in expected.items()):
            raise RuntimeError(f"Existing snapshot chunk conflicts with snapshot {chunk_id}")
        existing_ids.add(chunk_id)
    if len(existing_ids) == len(rows):
        return

    with collection.batch.dynamic() as batch:
        for index, row in enumerate(rows):
            if row["chunk_id"] not in existing_ids:
                batch.add_object(
                    properties=_properties(row, model_meta, checksums), vector=vectors[index].tolist(),
                    uuid=uuid.uuid5(uuid.NAMESPACE_URL, row["chunk_id"]),
                )
    failed = getattr(collection.batch, "failed_objects", [])
    if failed:
        raise RuntimeError(f"Weaviate rejected {len(failed)} snapshot objects")


def _write_active_config(config_path: Path, manifest: dict, snapshot_id: str, collection: str) -> None:
    corpus_db = manifest.get("corpus_db")
    if not corpus_db:
        raise ValueError("snapshot manifest does not pin corpus_db")
    original = config_path.read_text(encoding="utf-8")
    updated, db_count = re.subn(r"(?m)^(  db:\s*).+$", rf"\g<1>{corpus_db}", original, count=1)
    if db_count != 1:
        raise ValueError("could not locate mongo.db in config")
    block = ("active_snapshot:\n"
             f"  snapshot_id: {snapshot_id}\n"
             f"  manifest: data/snapshots/{snapshot_id}/manifest.json\n"
             f"  index_collection: {collection}\n"
             f"  corpus_db: {corpus_db}\n")
    updated, count = re.subn(r"(?ms)^active_snapshot:.*?(?=^[A-Za-z_][\w-]*:|\Z)", block + "\n", updated, count=1)
    if count != 1:
        updated = updated.rstrip() + "\n\n" + block
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=config_path.parent, prefix=".default-", delete=False) as tmp:
        temp_path = Path(tmp.name)
        tmp.write(updated)
        tmp.flush()
        os.fsync(tmp.fileno())
    os.chmod(temp_path, config_path.stat().st_mode)
    os.replace(temp_path, config_path)


def build_snapshot_index(snapshot_id: str, *, activate: bool = False, snapshots_dir: Path = ROOT / "data" / "snapshots",
                         config_path: Path = ROOT / "config" / "default.yaml", client: Any = None, model: Any = None) -> dict:
    manifest, rows, manifest_bytes, chunks_bytes = load_snapshot(snapshot_id, snapshots_dir)
    snapshot_dir = snapshots_dir / snapshot_id
    chunks_checksum = _sha256(chunks_bytes)
    model = model or get_embed_model()
    model_meta = _model_metadata(model, get_config(), batch_size=4)
    vectors, embeddings_checksum = _embeddings(snapshot_dir, rows, model_meta, chunks_checksum, model)
    if vectors.shape[0] != len(rows):
        raise RuntimeError(f"embedding count mismatch: {len(rows)} chunks, {vectors.shape[0]} vectors")

    collection = collection_name(snapshot_id)
    client = client or get_weaviate_client()
    if client is None or not client.is_ready():
        raise RuntimeError("Weaviate is unavailable")
    target = _ensure_collection(client, collection)
    checksums = {"manifest_sha256": _sha256(manifest_bytes), "chunks_sha256": chunks_checksum,
                 "embeddings_sha256": embeddings_checksum}
    _insert_missing(target, rows, vectors, model_meta, checksums)
    _verify_collection(target, rows, model_meta, checksums, vectors)
    if activate:
        _write_active_config(config_path, manifest, snapshot_id, collection)
    return {"snapshot_id": snapshot_id, "collection": collection, "chunks": len(rows),
            "model": model_meta, **checksums, "activated": activate}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and verify a snapshot-specific Weaviate index")
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--activate", action="store_true", help="Atomically make this verified snapshot active")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    client = get_weaviate_client()
    try:
        print(json.dumps(build_snapshot_index(args.snapshot_id, activate=args.activate, client=client), indent=2))
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()
