"""Run reproducible BERTopic over verified frozen snapshot embeddings."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from api.snapshot_evidence import load_active_snapshot
from core.config import get_config
from core.snapshot_index import ROOT, load_snapshot


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_snapshot_topic_inputs(
    snapshot_id: str | None = None, config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], np.ndarray, dict[str, Any]]:
    """Load ordered snapshot articles and verified normalized article embeddings."""
    cfg = config or get_config()
    active_id = (cfg.get("active_snapshot") or {}).get("snapshot_id")
    if not isinstance(active_id, str):
        raise ValueError("active snapshot is not configured")
    if snapshot_id is not None and snapshot_id != active_id:
        raise ValueError("topic runs are limited to the configured active snapshot")

    manifest, articles = load_active_snapshot(cfg)
    snapshot_id = manifest["snapshot_id"]
    snapshot_dir = ROOT / "data" / "snapshots" / snapshot_id
    _, chunks, manifest_bytes, chunks_bytes = load_snapshot(snapshot_id, snapshot_dir.parent)
    metadata_path = snapshot_dir / "embeddings.json"
    vectors_path = snapshot_dir / "embeddings.npy"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    chunks_hash = _sha256(chunks_bytes)
    expected_model = cfg.get("models", {}).get("embedder", "BAAI/bge-m3")
    expected_revision = manifest.get("nlp", {}).get("tokenizer", {}).get("revision")
    expected_settings = {
        "backend": "flagembedding", "return_dense": True,
        "return_sparse": False, "return_colbert_vecs": False,
    }
    if (
        metadata.get("snapshot_id") != snapshot_id
        or metadata.get("chunks_sha256") != chunks_hash
        or metadata.get("model") != expected_model
        or metadata.get("revision") != expected_revision
        or metadata.get("backend") != "flagembedding"
        or any(metadata.get("settings", {}).get(key) != value for key, value in expected_settings.items())
        or metadata.get("settings", {}).get("device") not in {"cpu", "cuda"}
        or not vectors_path.is_file()
        or _file_sha256(vectors_path) != metadata.get("embeddings_sha256")
    ):
        raise ValueError("snapshot embedding metadata or checksum is invalid")

    chunk_vectors = np.load(vectors_path, mmap_mode="r", allow_pickle=False)
    expected_chunks = manifest.get("counts", {}).get("chunks")
    if chunk_vectors.shape != (expected_chunks, 1024) or not np.isfinite(chunk_vectors).all():
        raise ValueError("snapshot embedding shape or values are invalid")

    article_ids = [str(article["article_id"]) for article in articles]
    if len(article_ids) != len(set(article_ids)):
        raise ValueError("snapshot article IDs are not unique")
    id_to_position = {article_id: position for position, article_id in enumerate(article_ids)}
    sums = np.zeros((len(article_ids), 1024), dtype=np.float64)
    counts = np.zeros(len(article_ids), dtype=np.int64)
    for row, vector in zip(chunks, chunk_vectors):
        position = id_to_position.get(str(row["article_id"]))
        if position is None:
            raise ValueError("snapshot chunk references an article outside the article manifest")
        sums[position] += vector
        counts[position] += 1
    if len(chunks) != len(chunk_vectors) or np.any(counts == 0):
        raise ValueError("snapshot chunks and ordered articles do not align")
    article_vectors = (sums / counts[:, None]).astype(np.float32)
    norms = np.linalg.norm(article_vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms == 0):
        raise ValueError("snapshot article embedding is not finite and nonzero")
    article_vectors /= norms
    provenance = {
        "manifest_sha256": _sha256(manifest_bytes),
        "articles_sha256": manifest["articles_sha256"],
        "chunks_sha256": chunks_hash,
        "embeddings_sha256": metadata["embeddings_sha256"],
        "embedding": metadata,
        "article_ids_sha256": _sha256(_canonical_json(article_ids)),
    }
    return manifest, articles, article_ids, article_vectors, provenance


def _settings(cfg: dict[str, Any]) -> dict[str, Any]:
    configured = cfg.get("topic_runs", {})
    clustering = cfg.get("clustering", {})
    return {
        "algorithm": "bertopic",
        "seed": int(clustering.get("random_seed", 42)),
        "umap": {
            "n_neighbors": int(configured.get("umap_n_neighbors", 15)),
            "n_components": int(clustering.get("umap_n_components", 5)),
            "min_dist": float(configured.get("umap_min_dist", 0.0)),
            "metric": "cosine",
            "low_memory": True,
            "n_jobs": 1,
        },
        "hdbscan": {
            "min_cluster_size": int(clustering.get("hdbscan_min_cluster_size", 15)),
            "min_samples": int(configured.get("hdbscan_min_samples", 5)),
            "metric": "euclidean",
            "cluster_selection_method": "eom",
            "prediction_data": False,
        },
        "vectorizer": {"ngram_range": [1, 2], "min_df": 2, "top_n_words": 10},
        "document_text": "title plus frozen article body",
        "article_embeddings": "mean of frozen chunk embeddings, L2 normalized",
    }


def _topic_records(topic_model: Any, labels: list[int], articles: list[dict[str, Any]],
                   article_ids: list[str]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    article_by_id = {str(article["article_id"]): article for article in articles}
    membership = dict(zip(article_ids, labels))
    members: dict[int, list[str]] = defaultdict(list)
    for article_id, label in membership.items():
        members[int(label)].append(article_id)
    representative_docs = getattr(topic_model, "representative_docs_", {}) or {}
    docs_to_ids: dict[str, list[str]] = defaultdict(list)
    for article_id, article in zip(article_ids, articles):
        docs_to_ids[f"{article.get('title', '')}\n{article['body']}"].append(article_id)

    topics = []
    for topic_id in sorted(members):
        ids = members[topic_id]
        terms = [term for term, _ in (topic_model.get_topic(topic_id) or [])[:10]] if topic_id != -1 else []
        representatives: list[str] = []
        for doc in representative_docs.get(topic_id, []):
            for candidate in docs_to_ids.get(doc, []):
                if candidate in ids and candidate not in representatives:
                    representatives.append(candidate)
                    break
            if len(representatives) == 3:
                break
        if not representatives:
            representatives = ids[:3]
        language_counts = Counter(article_by_id[article_id]["lang"] for article_id in ids)
        source_counts = Counter(article_by_id[article_id]["source_family"] for article_id in ids)
        topics.append({
            "id": topic_id,
            "label": "Unassigned" if topic_id == -1 else ", ".join(terms[:3]) or f"Topic {topic_id}",
            "size": len(ids),
            "article_ids": ids,
            "top_terms": terms,
            "lang_counts": dict(sorted(language_counts.items())),
            "source_counts": dict(sorted(source_counts.items())),
            "representative_article_ids": representatives,
        })
    return topics, membership


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def run_snapshot_topics(snapshot_id: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run real BERTopic against the verified active snapshot and atomically activate its artifacts."""
    cfg = config or get_config()
    manifest, articles, article_ids, article_vectors, provenance = load_snapshot_topic_inputs(snapshot_id, cfg)
    settings = _settings(cfg)
    settings_hash = _sha256(_canonical_json(settings))
    run_id = f"bertopic-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = time.perf_counter()

    from bertopic import BERTopic
    from hdbscan import HDBSCAN
    from sklearn.feature_extraction.text import CountVectorizer
    from umap import UMAP

    umap_settings = settings["umap"]
    hdbscan_settings = settings["hdbscan"]
    umap_model = UMAP(**umap_settings, random_state=settings["seed"])
    hdbscan_model = HDBSCAN(**hdbscan_settings)
    vectorizer_model = CountVectorizer(ngram_range=(1, 2), min_df=2, token_pattern=r"(?u)\b\w+\b")
    topic_model = BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        top_n_words=10,
        calculate_probabilities=False,
        verbose=True,
    )
    documents = [f"{article.get('title', '')}\n{article['body']}" for article in articles]
    labels, _ = topic_model.fit_transform(documents, article_vectors)
    topics, membership = _topic_records(topic_model, [int(label) for label in labels], articles, article_ids)
    if set(membership) != set(article_ids) or any(topic["size"] != len(topic["article_ids"]) for topic in topics):
        raise RuntimeError("BERTopic output does not contain exact snapshot article memberships")
    topics_payload = {"snapshot_id": manifest["snapshot_id"], "run_id": run_id, "topics": topics}
    topics_bytes = json.dumps(topics_payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    run = {
        "run_id": run_id,
        "algorithm": "bertopic",
        "snapshot_id": manifest["snapshot_id"],
        "snapshot_manifest_sha256": provenance["manifest_sha256"],
        "settings_hash": settings_hash,
        "article_ids": article_ids,
        "article_ids_sha256": provenance["article_ids_sha256"],
        "memberships": membership,
        "topic_count": sum(topic["id"] != -1 for topic in topics),
        "outlier_count": sum(topic["size"] for topic in topics if topic["id"] == -1),
        "outlier_article_ids": next((topic["article_ids"] for topic in topics if topic["id"] == -1), []),
        "settings": settings,
        "provenance": provenance,
        "versions": {name: importlib.metadata.version(name) for name in ("bertopic", "umap-learn", "hdbscan", "numpy", "scikit-learn")},
        "hardware": {"platform": platform.platform(), "processor": platform.processor(), "cpu_count": os.cpu_count(), "accelerator": "CPU"},
        "started_at": started_at,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "topics_sha256": _sha256(topics_bytes),
    }
    root = ROOT / str(cfg.get("topic_runs", {}).get("root", "data/topic_runs"))
    output_dir = root / manifest["snapshot_id"] / settings_hash / run_id
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix=f".{run_id}-", dir=output_dir.parent))
    try:
        (temp_dir / "topics.json").write_bytes(topics_bytes)
        _atomic_json(temp_dir / "topic_run.json", run)
        if output_dir.exists():
            raise FileExistsError(output_dir)
        os.replace(temp_dir, output_dir)
    except Exception:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    active_pointer = ROOT / str(cfg.get("topic_runs", {}).get("active_pointer", "data/topic_runs/active.json"))
    pointer = {
        "snapshot_id": manifest["snapshot_id"], "settings_hash": settings_hash, "run_id": run_id,
        "topic_run_sha256": _file_sha256(output_dir / "topic_run.json"),
        "topics_sha256": _file_sha256(output_dir / "topics.json"),
    }
    _atomic_json(active_pointer, pointer)
    return run


def load_active_topic_run(
    snapshot_id: str, article_ids: list[str], config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Load and verify activated topic artifacts for exactly the requested snapshot articles."""
    cfg = config or get_config()
    topic_cfg = cfg.get("topic_runs", {})
    root = (ROOT / str(topic_cfg.get("root", "data/topic_runs"))).resolve()
    pointer_path = (ROOT / str(topic_cfg.get("active_pointer", "data/topic_runs/active.json"))).resolve()
    if pointer_path != (root / "active.json").resolve():
        raise ValueError("topic pointer must be inside the configured topic run root")
    if not pointer_path.is_file():
        return None
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if pointer.get("snapshot_id") != snapshot_id:
        return None
    settings_hash, run_id = pointer.get("settings_hash"), pointer.get("run_id")
    if not isinstance(settings_hash, str) or len(settings_hash) != 64 or not isinstance(run_id, str) or "/" in run_id:
        raise ValueError("active topic pointer is invalid")
    run_dir = (root / snapshot_id / settings_hash / run_id).resolve()
    if not run_dir.is_relative_to(root):
        raise ValueError("active topic artifact path escapes the topic run root")
    run_path, topics_path = run_dir / "topic_run.json", run_dir / "topics.json"
    if (
        not run_path.is_file() or not topics_path.is_file()
        or _file_sha256(run_path) != pointer.get("topic_run_sha256")
        or _file_sha256(topics_path) != pointer.get("topics_sha256")
    ):
        raise ValueError("active topic artifact is missing or its checksum does not match")
    run = json.loads(run_path.read_text(encoding="utf-8"))
    topics_payload = json.loads(topics_path.read_text(encoding="utf-8"))
    topics = topics_payload.get("topics")
    expected_provenance = load_snapshot_topic_inputs(snapshot_id, cfg)[-1]
    if (
        run.get("snapshot_id") != snapshot_id or run.get("run_id") != run_id
        or run.get("settings_hash") != settings_hash
        or run.get("topics_sha256") != _file_sha256(topics_path)
        or topics_payload.get("snapshot_id") != snapshot_id or topics_payload.get("run_id") != run_id
        or run.get("article_ids") != article_ids
        or run.get("article_ids_sha256") != _sha256(_canonical_json(article_ids))
        or run.get("provenance") != expected_provenance
        or not isinstance(topics, list)
    ):
        raise ValueError("active topic artifact provenance does not match the frozen snapshot")
    memberships = run.get("memberships")
    if not isinstance(memberships, dict) or set(memberships) != set(article_ids):
        raise ValueError("active topic artifact memberships do not cover the snapshot")
    flattened: list[str] = []
    for topic in topics:
        topic_ids = topic.get("article_ids")
        if not isinstance(topic_ids, list) or topic.get("size") != len(topic_ids):
            raise ValueError("active topic artifact has invalid topic members")
        topic_id = str(topic.get("id"))
        if any(memberships.get(article_id) != topic.get("id") for article_id in topic_ids):
            raise ValueError("active topic artifact membership lists disagree")
        flattened.extend(topic_ids)
    if len(flattened) != len(article_ids) or set(flattened) != set(article_ids):
        raise ValueError("active topic artifact does not assign every article exactly once")
    return run, topics


def activate_snapshot_topics(snapshot_id: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run and activate a new immutable topic artifact; prior pointers survive failures."""
    return run_snapshot_topics(snapshot_id, config)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run BERTopic over the verified active article snapshot")
    parser.add_argument("--snapshot-id", default=None)
    args = parser.parse_args()
    result = run_snapshot_topics(args.snapshot_id)
    print(json.dumps({key: result[key] for key in ("run_id", "snapshot_id", "settings_hash", "topic_count", "outlier_count", "duration_seconds")}, indent=2))
