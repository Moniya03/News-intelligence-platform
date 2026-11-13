"""Bounded, reproducible retrieval pool and held-out evaluation for a frozen snapshot."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from core.snapshot_index import load_snapshot

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_ID = "corpus-59b2b589fe3bbdbffdc3"
ARTIFACTS = ROOT / "artifacts/retrieval_eval/v1"
QUERIES = ARTIFACTS / "queries.jsonl"
FREEZE = ARTIFACTS / "query_freeze.json"
SEED = 42
LANGUAGES = {"en", "hi", "bn", "mr"}
MODES = ("bm25", "dense", "hybrid")
JUDGMENTS = ARTIFACTS / "judgments.jsonl"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_sha(path: Path) -> str:
    return _sha(path.read_bytes())


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def validate_queries(path: Path = QUERIES) -> tuple[list[dict[str, Any]], str]:
    rows = _jsonl(path)
    required = {"id", "split", "query_lang", "need_type", "text", "intent", "evidence_expectations"}
    if len(rows) != 60:
        raise ValueError(f"expected 60 queries, found {len(rows)}")
    ids: set[str] = set()
    by_split_lang: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if set(row) != required:
            raise ValueError(f"query fields must be exactly {sorted(required)}")
        if not all(isinstance(row[k], str) and row[k].strip() for k in ("id", "split", "query_lang", "need_type", "text", "intent")):
            raise ValueError("query identity, language, type, text, and intent must be non-empty strings")
        if row["id"] in ids:
            raise ValueError(f"duplicate query id: {row['id']}")
        ids.add(row["id"])
        if row["split"] not in {"dev", "test"} or row["query_lang"] not in LANGUAGES:
            raise ValueError(f"invalid split or query language for {row['id']}")
        if row["need_type"] not in {"same_language", "cross_language", "multilingual"}:
            raise ValueError(f"invalid need_type for {row['id']}")
        if not isinstance(row["evidence_expectations"], list) or not row["evidence_expectations"] or any(not isinstance(x, str) or not x.strip() for x in row["evidence_expectations"]):
            raise ValueError(f"evidence_expectations must be a non-empty string list for {row['id']}")
        # Support IDs and relevance labels belong in separate, post-freeze annotation files.
        if any(k in row for k in ("article_id", "article_ids", "relevant_ids", "gold", "qrels")):
            raise ValueError(f"query file contains answer labels for {row['id']}")
        by_split_lang[(row["split"], row["query_lang"])].append(row)
    for lang in LANGUAGES:
        dev = by_split_lang[("dev", lang)]
        test = by_split_lang[("test", lang)]
        if len(dev) != 3 or len(test) != 12:
            raise ValueError(f"expected 3 dev and 12 test queries for {lang}")
        counts = {kind: sum(row["need_type"] == kind for row in test) for kind in ("same_language", "cross_language", "multilingual")}
        if counts != {"same_language": 4, "cross_language": 4, "multilingual": 4}:
            raise ValueError(f"test queries for {lang} need four of each type; found {counts}")
    return rows, _file_sha(path)


def _snapshot_fingerprint(snapshot_id: str) -> dict[str, str]:
    manifest, rows, manifest_bytes, chunks_bytes = load_snapshot(snapshot_id)
    snapshot_dir = ROOT / "data/snapshots" / snapshot_id
    embeddings_path = snapshot_dir / "embeddings.json"
    vectors_path = snapshot_dir / "embeddings.npy"
    if not embeddings_path.is_file():
        raise FileNotFoundError(f"verified snapshot embedding metadata missing: {embeddings_path}")
    if not vectors_path.is_file():
        raise FileNotFoundError(f"verified snapshot vectors missing: {vectors_path}")
    embeddings = json.loads(embeddings_path.read_text(encoding="utf-8"))
    if embeddings.get("snapshot_id") != snapshot_id or embeddings.get("chunks_sha256") != _sha(chunks_bytes):
        raise ValueError("snapshot embedding metadata does not match frozen chunks")
    vectors_sha = _file_sha(vectors_path)
    if embeddings.get("embeddings_sha256") != vectors_sha:
        raise ValueError("snapshot vector checksum does not match embedding metadata")
    if manifest.get("counts", {}).get("chunks") != len(rows):
        raise ValueError("snapshot manifest chunk count mismatch")
    return {
        "manifest_sha256": _sha(manifest_bytes),
        "chunks_sha256": _sha(chunks_bytes),
        "embeddings_sha256": vectors_sha,
        "embedding_metadata_sha256": _file_sha(embeddings_path),
    }


def freeze_queries(snapshot_id: str = SNAPSHOT_ID, query_path: Path = QUERIES, freeze_path: Path = FREEZE) -> dict[str, Any]:
    _, query_sha = validate_queries(query_path)
    record = {"schema_version": 1, "snapshot_id": snapshot_id, "queries_sha256": query_sha,
              "snapshot": _snapshot_fingerprint(snapshot_id), "seed": SEED,
              "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    if freeze_path.exists():
        previous = json.loads(freeze_path.read_text(encoding="utf-8"))
        if any(previous.get(key) != record.get(key) for key in ("snapshot_id", "queries_sha256", "snapshot", "seed")):
            raise FileExistsError(f"refusing to replace different query freeze record: {freeze_path}")
        return previous
    freeze_path.write_text(payload, encoding="utf-8")
    return record


def _require_frozen(query_path: Path, freeze_path: Path, snapshot_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows, query_sha = validate_queries(query_path)
    record = json.loads(freeze_path.read_text(encoding="utf-8"))
    if record.get("snapshot_id") != snapshot_id or record.get("queries_sha256") != query_sha:
        raise ValueError("query freeze does not match current query file and snapshot")
    if record.get("snapshot") != _snapshot_fingerprint(snapshot_id):
        raise ValueError("frozen snapshot files have changed")
    return rows, record


def _model_metadata(model: Any, cfg: dict[str, Any]) -> dict[str, Any]:
    if getattr(model, "backend", None) != "flagembedding":
        raise RuntimeError("retrieval evaluation requires the real BGE-M3 FlagEmbedding backend")
    import torch
    cache = Path.home() / ".cache/huggingface/hub/models--BAAI--bge-m3/snapshots"
    revisions = sorted(p.name for p in cache.iterdir() if p.is_dir()) if cache.is_dir() else []
    if not revisions:
        raise RuntimeError("cached BGE-M3 revision is unavailable")
    device = "cuda" if torch.cuda.is_available() and model.device == "cuda" else "cpu"
    return {"model": cfg.get("models", {}).get("embedder", "BAAI/bge-m3"), "revision": revisions[0],
            "backend": model.backend, "device": device,
            "settings": {"fp16": bool(model.fp16 and device == "cuda"), "max_length": 512,
                         "batch_size": 1, "return_dense": True, "return_sparse": False,
                         "return_colbert_vecs": False}}


def _article_rank(chunks: list[dict[str, Any]], allowed_ids: set[str]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        article_id = str(chunk.get("article_id", ""))
        score = chunk.get("score")
        if not article_id or article_id not in allowed_ids or type(score) not in (float, int) or not math.isfinite(float(score)):
            raise ValueError("retrieval returned invalid article identity or score")
        if chunk.get("snapshot_id") != SNAPSHOT_ID:
            raise ValueError("retrieval returned a chunk outside the frozen snapshot")
        if article_id not in seen:
            seen.add(article_id)
            ranked.append({"article_id": article_id, "score": float(score), "chunk_id": str(chunk.get("chunk_id", ""))})
            if len(ranked) == 5:
                break
    return ranked


def run_retrieval(snapshot_id: str = SNAPSHOT_ID, query_path: Path = QUERIES, freeze_path: Path = FREEZE,
                  output_path: Path | None = None, split: str = "test") -> dict[str, Any]:
    rows, freeze = _require_frozen(query_path, freeze_path, snapshot_id)
    if split not in {"dev", "test"}:
        raise ValueError("retrieval split must be dev or test")
    selected_rows = [q for q in rows if q["split"] == split]
    _, snapshot_chunks, _, _ = load_snapshot(snapshot_id)
    allowed_ids = {str(row["article_id"]) for row in snapshot_chunks}
    from core.config import get_config
    from core.embed import get_embed_model
    from core.index import get_weaviate_client
    from core.retrieve import retrieve_bm25, retrieve_dense, retrieve_hybrid

    cfg = get_config()
    active = cfg.get("active_snapshot", {})
    if active.get("snapshot_id") != snapshot_id or not active.get("index_collection"):
        raise ValueError("configured active index does not match the frozen snapshot")
    model = get_embed_model()
    model_meta = _model_metadata(model, cfg)
    indexed_model = json.loads((ROOT / "data/snapshots" / snapshot_id / "embeddings.json").read_text(encoding="utf-8"))
    if any(model_meta[key] != indexed_model.get(key) for key in ("model", "revision", "backend")):
        raise ValueError("query embedder differs from the frozen index model")
    client = get_weaviate_client()
    if client is None or (hasattr(client, "is_ready") and not client.is_ready()):
        raise RuntimeError("verified Weaviate snapshot index is unavailable")

    run_rows: list[dict[str, Any]] = []
    try:
        for query in selected_rows:
            query_id = query["id"]
            embedding_start = time.perf_counter()
            vector = model.embed_query(query["text"])
            embedding_ms = (time.perf_counter() - embedding_start) * 1000
            rankings: dict[str, list[dict[str, Any]]] = {}
            timings: dict[str, float] = {}
            # 150 exceeds five times this verified snapshot's maximum of 23 chunks per article.
            for mode, call in (
                ("bm25", lambda: retrieve_bm25(query["text"], client, top_k=150)),
                ("dense", lambda: retrieve_dense(vector, client, top_k=150)),
                ("hybrid", lambda: retrieve_hybrid(vector, query["text"], client, top_k=150,
                                                    alpha=float(cfg.get("retrieval", {}).get("hybrid_alpha", 0.7)))),
            ):
                started = time.perf_counter()
                chunks = call()
                timings[mode] = (time.perf_counter() - started) * 1000
                rankings[mode] = _article_rank(chunks, allowed_ids)
            run_rows.append({"query_id": query_id, "split": query["split"], "query_lang": query["query_lang"], "need_type": query["need_type"],
                             "embedding_latency_ms": embedding_ms, "retrieval_latency_ms": timings,
                             "latency_ms": {"bm25": timings["bm25"], "dense": timings["dense"] + embedding_ms,
                                            "hybrid": timings["hybrid"] + embedding_ms}, "rankings": rankings})
    finally:
        if hasattr(client, "close"):
            client.close()

    run = {
        "schema_version": 1, "status": "unjudged", "snapshot_id": snapshot_id,
        "queries_sha256": freeze["queries_sha256"], "snapshot": freeze["snapshot"],
        "split": split, "query_count": len(selected_rows), "systems": list(MODES), "reranker": "omitted before pool freeze",
        "settings": {"candidate_chunks": 150, "unique_articles": 5, "language_filter": None,
                     "hybrid_alpha": float(cfg.get("retrieval", {}).get("hybrid_alpha", 0.7)), "seed": SEED},
        "model": model_meta,
        "hardware": {"device": model_meta["device"],
                     "gpu": __import__("torch").cuda.get_device_name(0) if model_meta["device"] == "cuda" else None},
        "versions": {"python": sys.version.split()[0], **{name: importlib.metadata.version(name) for name in ("numpy", "weaviate-client", "torch")}},
        "query_rows": run_rows,
    }
    if output_path is None:
        output_path = ARTIFACTS / "runs" / snapshot_id / "baseline.json"
    _write_json(output_path, run)
    return run


def build_pool(run_path: Path, query_path: Path = QUERIES, freeze_path: Path = FREEZE,
               pool_path: Path | None = None, packets_path: Path | None = None) -> dict[str, Any]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    queries, freeze = _require_frozen(query_path, freeze_path, str(run.get("snapshot_id")))
    if run.get("status") != "unjudged" or run.get("systems") != list(MODES):
        raise ValueError("pooling requires one unjudged BM25/dense/hybrid run")
    expected_ids = {q["id"] for q in queries if q["split"] == "test"}
    run_rows = run.get("query_rows", [])
    run_ids = [row.get("query_id") for row in run_rows]
    if len(run_rows) != 48 or len(set(run_ids)) != 48 or set(run_ids) != expected_ids or run.get("queries_sha256") != freeze["queries_sha256"]:
        raise ValueError("run query set or checksum differs from frozen held-out queries")
    for row in run_rows:
        if set(row.get("rankings", {})) != set(MODES):
            raise ValueError("run is missing a required retrieval mode")
        for mode in MODES:
            articles = [r.get("article_id") for r in row["rankings"][mode]]
            if len(articles) > 5 or len(articles) != len(set(articles)):
                raise ValueError("run rankings must contain at most five unique articles per mode")
    _, chunks, _, _ = load_snapshot(str(run["snapshot_id"]))
    by_article: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        by_article.setdefault(str(chunk["article_id"]), chunk)
    query_by_id = {q["id"]: q for q in queries}
    query_ids = {row["query_id"] for row in run["query_rows"]}
    packets = []
    pool_meta = []
    for query_id in sorted(query_ids):
        candidates: dict[str, list[str]] = defaultdict(list)
        for mode in MODES:
            for row in run["query_rows"]:
                if row["query_id"] != query_id:
                    continue
                for result in row["rankings"][mode]:
                    candidates[result["article_id"]].append(mode)
        articles = sorted(candidates)
        random.Random(f"{SEED}:{query_id}").shuffle(articles)
        for index, article_id in enumerate(articles, 1):
            candidate_id = f"c{index:03d}"
            chunk = by_article.get(article_id)
            if chunk is None:
                raise ValueError(f"pooled article missing from frozen snapshot: {article_id}")
            pool_meta.append({"query_id": query_id, "candidate_id": candidate_id, "article_id": article_id,
                              "systems": sorted(set(candidates[article_id]))})
            packets.append({"query_id": query_id, "query": query_by_id[query_id]["text"],
                            "query_lang": query_by_id[query_id]["query_lang"], "candidate_id": candidate_id,
                            "title": chunk["title"], "url": chunk["original_url"],
                            "excerpt": str(chunk["text"])[:600]})
    packets.sort(key=lambda row: (row["query_id"], row["candidate_id"]))
    packets_bytes = "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n" for p in packets).encode("utf-8")
    pool_path = pool_path or (ARTIFACTS / "pools" / str(run["snapshot_id"]) / "pool.json")
    packets_path = packets_path or (ROOT / "data/retrieval_eval" / str(run["snapshot_id"]) / "judging_packets.jsonl")
    pool = {"schema_version": 1, "status": "unjudged", "snapshot_id": run["snapshot_id"],
            "queries_sha256": run["queries_sha256"], "run_sha256": _file_sha(run_path), "seed": SEED,
            "packets_sha256": _sha(packets_bytes),
            "candidate_pairs": len(pool_meta), "candidate_map": pool_meta}
    _write_json(pool_path, pool)
    packets_path.parent.mkdir(parents=True, exist_ok=True)
    packets_path.write_bytes(packets_bytes)
    return pool


def _metric(rank: list[str], grades: dict[str, int], pool_grades: dict[str, int]) -> dict[str, float | None]:
    ranked_grades = [(index, article) for index, article in enumerate(rank[:5]) if article in grades]
    rel_pool = {article for article, grade in pool_grades.items() if grade >= 1}
    dcg = sum((2 ** grades[article] - 1) / math.log2(index + 2) for index, article in ranked_grades if grades[article] > 0)
    ideal = sorted((grade for grade in pool_grades.values()), reverse=True)[:5]
    idcg = sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
    rr = next((1 / (index + 1) for index, article in ranked_grades if grades[article] >= 1), 0.0)
    relevant_count = len(rel_pool)
    recall = sum(article in rel_pool for article in rank[:5]) / relevant_count if relevant_count else None
    return {"ndcg5": dcg / idcg if idcg else None, "mrr5": rr if relevant_count else None,
            "recall5_pooled": recall}


def _validate_run(run: dict[str, Any], query_rows: list[dict[str, Any]], freeze: dict[str, Any]) -> list[dict[str, Any]]:
    expected = {q["id"]: q for q in query_rows if q["split"] == "test"}
    rows = run.get("query_rows")
    if run.get("status") != "unjudged" or run.get("systems") != list(MODES):
        raise ValueError("run must be the unjudged BM25/dense/hybrid output")
    if run.get("queries_sha256") != freeze.get("queries_sha256") or len(rows or []) != 48:
        raise ValueError("run does not contain the frozen held-out query set")
    ids = [row.get("query_id") for row in rows]
    if len(set(ids)) != 48 or set(ids) != set(expected):
        raise ValueError("run must contain exactly one row per held-out query")
    allowed_articles = {str(row["article_id"]) for row in load_snapshot(str(run["snapshot_id"]))[1]}
    for row in rows:
        query = expected[row["query_id"]]
        if row.get("query_lang") != query["query_lang"] or row.get("need_type") != query["need_type"]:
            raise ValueError("run query metadata differs from the frozen query")
        rankings = row.get("rankings")
        if not isinstance(rankings, dict) or set(rankings) != set(MODES):
            raise ValueError("run is missing a retrieval mode")
        for mode in MODES:
            results = rankings[mode]
            article_ids = [result.get("article_id") for result in results]
            if len(results) > 5 or len(set(article_ids)) != len(article_ids):
                raise ValueError("run rankings must contain at most five unique articles per mode")
            for result in results:
                if result.get("article_id") not in allowed_articles or type(result.get("score")) not in (int, float) or not math.isfinite(float(result["score"])):
                    raise ValueError("run ranking has invalid article identity or score")
                if not isinstance(result.get("chunk_id"), str) or not result["chunk_id"]:
                    raise ValueError("run ranking is missing the contributing chunk ID")
    return rows


def _incomplete_score(run: dict[str, Any], run_path: Path, pool_path: Path, pool: dict[str, Any], reason: str,
                     output_path: Path | None, packets_path: Path) -> dict[str, Any]:
    result = {"schema_version": 1, "status": "incomplete", "snapshot_id": run["snapshot_id"],
              "run_sha256": _file_sha(run_path),
              "pool_sha256": _file_sha(pool_path), "packets_sha256": _file_sha(packets_path),
              "candidate_pairs": pool.get("candidate_pairs"),
              "metrics": None, "reason": reason}
    output_path = output_path or (ARTIFACTS / "scores" / str(run["snapshot_id"]) / "scores.json")
    _write_json(output_path, result)
    return result


def score_run(run_path: Path, pool_path: Path, judgments_path: Path = JUDGMENTS,
              output_path: Path | None = None, packets_path: Path | None = None) -> dict[str, Any]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    if pool.get("run_sha256") != _file_sha(run_path) or pool.get("snapshot_id") != run.get("snapshot_id") or pool.get("queries_sha256") != run.get("queries_sha256") or pool.get("status") != "unjudged":
        raise ValueError("pool does not match retrieval run")
    if not isinstance(pool.get("candidate_map"), list):
        raise ValueError("pool candidate_map must be a list")
    packets_path = packets_path or (ROOT / "data/retrieval_eval" / str(run["snapshot_id"]) / "judging_packets.jsonl")
    if not packets_path.is_file() or pool.get("packets_sha256") != _file_sha(packets_path):
        raise ValueError("judging packets do not match the immutable pool checksum")
    try:
        mapping = {(r["query_id"], r["candidate_id"]): r["article_id"] for r in pool["candidate_map"]}
    except (KeyError, TypeError):
        raise ValueError("pool contains malformed candidate rows") from None
    if len(mapping) != pool.get("candidate_pairs"):
        raise ValueError("pool contains duplicate query/candidate IDs")
    queries, freeze = _require_frozen(QUERIES, FREEZE, str(run.get("snapshot_id")))
    run_rows = _validate_run(run, queries, freeze)
    expected_map: dict[tuple[str, str], str] = {}
    for run_row in run_rows:
        query_id = run_row["query_id"]
        articles = sorted({result["article_id"] for mode in MODES for result in run_row["rankings"][mode]})
        random.Random(f"{SEED}:{query_id}").shuffle(articles)
        expected_map.update({(query_id, f"c{index:03d}"): article_id
                             for index, article_id in enumerate(articles, 1)})
    if mapping != expected_map:
        raise ValueError("pool candidate IDs do not match the deterministic run-derived assignment")
    candidates_by_query: dict[str, set[str]] = defaultdict(set)
    for row in pool["candidate_map"]:
        key = (row.get("query_id"), row.get("candidate_id"))
        if not all(isinstance(value, str) and value for value in key) or not isinstance(row.get("article_id"), str) or not isinstance(row.get("systems"), list) or not set(row["systems"]) <= set(MODES):
            raise ValueError("pool contains invalid candidate identity or systems")
        if row["article_id"] in candidates_by_query[row["query_id"]]:
            raise ValueError("pool contains a duplicate article for a query")
        candidates_by_query[row["query_id"]].add(row["article_id"])
    expected_candidates: dict[str, set[str]] = defaultdict(set)
    expected_systems: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in run_rows:
        for mode in MODES:
            for result in row["rankings"][mode]:
                article_id = result["article_id"]
                expected_candidates[row["query_id"]].add(article_id)
                expected_systems[(row["query_id"], article_id)].add(mode)
    actual_candidates = {qid: ids for qid, ids in candidates_by_query.items()}
    if actual_candidates != dict(expected_candidates):
        raise ValueError("pool candidates do not match the union of the frozen run rankings")
    for row in pool["candidate_map"]:
        if set(row["systems"]) != expected_systems[(row["query_id"], row["article_id"])]:
            raise ValueError("pool system provenance does not match the retrieval rankings")
    if not mapping:
        return _incomplete_score(run, run_path, pool_path, pool, "the retrieval pool is empty", output_path, packets_path)
    if not judgments_path.is_file():
        return _incomplete_score(run, run_path, pool_path, pool, "human judgments are not available; metrics were not calculated", output_path, packets_path)
    judgments = _jsonl(judgments_path)
    by_candidate: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in judgments:
        key = (row.get("query_id"), row.get("candidate_id"))
        if key not in mapping or not isinstance(row.get("judge_id"), str) or not row["judge_id"].strip():
            raise ValueError("judgment references an unknown candidate or has no judge_id")
        grade = row.get("grade")
        status = row.get("status", "judged")
        if status == "judged" and (type(grade) is not int or grade not in (0, 1, 2)):
            raise ValueError("judged grade must be 0, 1, or 2")
        if status == "unjudgeable" and grade is not None:
            raise ValueError("unjudgeable judgment must have a null grade")
        if status not in {"judged", "unjudgeable"}:
            raise ValueError("judgment status must be judged or unjudgeable")
        has_adjudication = any(key in row for key in ("adjudicated_status", "adjudicated_grade", "adjudicator_id"))
        if has_adjudication:
            final_status = row.get("adjudicated_status")
            final_grade = row.get("adjudicated_grade")
            if (final_status not in {"judged", "unjudgeable"} or
                    (final_status == "judged" and (type(final_grade) is not int or final_grade not in (0, 1, 2))) or
                    (final_status == "unjudgeable" and final_grade is not None) or
                    not isinstance(row.get("adjudicator_id"), str) or not row["adjudicator_id"].strip()):
                raise ValueError("adjudication requires final status, valid grade, and non-empty adjudicator_id")
        if any(existing["judge_id"] == row["judge_id"] for existing in by_candidate[key]):
            raise ValueError("duplicate judgment by the same judge")
        by_candidate[key].append({**row, "status": status})
    missing = len(set(mapping) - set(by_candidate))
    if missing:
        return _incomplete_score(run, run_path, pool_path, pool, f"{missing} pooled candidates have no judgment", output_path)
    double = [rows for rows in by_candidate.values() if len(rows) >= 2]
    if len(double) / len(mapping) < 0.20:
        return _incomplete_score(run, run_path, pool_path, pool, "fewer than 20% of pooled pairs are double-judged", output_path)
    comparable = [(left, right) for rs in double for i, left in enumerate(rs) for right in rs[i + 1:]]
    label = lambda row: (row["status"], row.get("grade") if row["status"] == "judged" else None)
    agreement = sum(label(left) == label(right) for left, right in comparable) / len(comparable) if comparable else None
    disagreements = 0
    adjudicated_disagreements = 0
    for key, rows in by_candidate.items():
        if len({label(r) for r in rows}) > 1:
            disagreements += 1
            adjudicated = {(r["adjudicated_status"], r.get("adjudicated_grade")) for r in rows if "adjudicated_status" in r}
            if len(adjudicated) != 1:
                return _incomplete_score(run, run_path, pool_path, pool,
                                         f"disagreement not adjudicated for {key[0]}/{key[1]}", output_path, packets_path)
            adjudicated_disagreements += 1

    judged: dict[str, dict[str, int]] = defaultdict(dict)
    unjudgeable = 0
    for (query_id, candidate_id), rows in by_candidate.items():
        article_id = mapping[(query_id, candidate_id)]
        adjudicated = {(r["adjudicated_status"], r.get("adjudicated_grade")) for r in rows if "adjudicated_status" in r}
        if adjudicated:
            final_status, grade = next(iter(adjudicated))
        else:
            labels = {label(row) for row in rows}
            if len(labels) != 1:
                raise ValueError(f"conflicting judgments for {query_id}/{candidate_id}")
            final_status, grade = next(iter(labels))
        if final_status == "unjudgeable":
            unjudgeable += 1
            continue
        judged[query_id][article_id] = int(grade)

    query_meta = {row["id"]: row for row in _jsonl(QUERIES)}
    per_query: dict[str, Any] = {}
    rows_by_query = {r["query_id"]: r for r in run["query_rows"]}
    for query_id, query_row in rows_by_query.items():
        grades = judged.get(query_id, {})
        per_query[query_id] = {"query_lang": query_meta[query_id]["query_lang"], "need_type": query_meta[query_id]["need_type"],
                               "judged_relevant_pool": sum(g >= 1 for g in grades.values()),
                               "metrics": {mode: _metric([r["article_id"] for r in query_row["rankings"][mode]], grades, grades) for mode in MODES}}
    metrics: dict[str, Any] = {"per_query": per_query, "by_language_and_need_type": {}, "macro": {},
                               "no_judged_relevant_queries": sum(not r["judged_relevant_pool"] for r in per_query.values()),
                               "unjudgeable_pairs_excluded": unjudgeable,
                               "pooled_recall_limit": "Recall@5 is relative to this judged pool, not exhaustive corpus recall.",
                               "judged_candidate_pairs": len(mapping) - unjudgeable,
                               "agreement_raw": {"double_judged_candidates": len(double), "comparable_judge_pairs": len(comparable),
                                                 "disagreement_candidates": disagreements, "adjudicated_disagreements": adjudicated_disagreements,
                                                 "percent": agreement}}
    metrics["mean_latency_ms"] = {mode: _mean([row["latency_ms"][mode] for row in run["query_rows"]]) for mode in MODES}
    for mode in MODES:
        metric_names = ("ndcg5", "mrr5", "recall5_pooled")
        values = {name: [q["metrics"][mode][name] for q in per_query.values() if q["metrics"][mode][name] is not None] for name in metric_names}
        metrics["macro"][mode] = {name: _mean(rows) for name, rows in values.items()}
        metrics["macro"][mode]["query_denominators"] = {name: len(rows) for name, rows in values.items()}
    for lang in sorted(LANGUAGES):
        for need in ("same_language", "cross_language", "multilingual"):
            selected = [qid for qid, meta in query_meta.items() if meta["query_lang"] == lang and meta["need_type"] == need and qid in per_query]
            metrics["by_language_and_need_type"][f"{lang}:{need}"] = {
                mode: {name: _mean([per_query[qid]["metrics"][mode][name] for qid in selected if per_query[qid]["metrics"][mode][name] is not None])
                       for name in ("ndcg5", "mrr5", "recall5_pooled")} for mode in MODES}
            metrics["by_language_and_need_type"][f"{lang}:{need}"]["query_counts"] = {
                "total": len(selected), "no_judged_relevant": sum(not per_query[qid]["judged_relevant_pool"] for qid in selected)}
            for mode in MODES:
                metrics["by_language_and_need_type"][f"{lang}:{need}"][mode]["query_denominators"] = {
                    name: sum(per_query[qid]["metrics"][mode][name] is not None for qid in selected)
                    for name in ("ndcg5", "mrr5", "recall5_pooled")}
    result = {"schema_version": 1, "status": "complete", "snapshot_id": run["snapshot_id"],
              "run_sha256": _file_sha(run_path), "pool_sha256": _file_sha(pool_path),
              "packets_sha256": _file_sha(packets_path), "metrics": metrics}
    output_path = output_path or (ARTIFACTS / "scores" / str(run["snapshot_id"]) / "scores.json")
    _write_json(output_path, result)
    return result


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--queries", type=Path, default=QUERIES)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--snapshot-id", default=SNAPSHOT_ID)
    freeze.add_argument("--queries", type=Path, default=QUERIES)
    freeze.add_argument("--output", type=Path, default=FREEZE)
    run = sub.add_parser("run")
    run.add_argument("--snapshot-id", default=SNAPSHOT_ID)
    run.add_argument("--queries", type=Path, default=QUERIES)
    run.add_argument("--freeze", type=Path, default=FREEZE)
    run.add_argument("--output", type=Path, default=None)
    run.add_argument("--split", choices=("dev", "test"), default="test")
    pool = sub.add_parser("pool")
    pool.add_argument("--run", type=Path, required=True)
    pool.add_argument("--queries", type=Path, default=QUERIES)
    pool.add_argument("--freeze", type=Path, default=FREEZE)
    pool.add_argument("--output", type=Path, default=None)
    pool.add_argument("--packets", type=Path, default=None)
    score = sub.add_parser("score")
    score.add_argument("--run", type=Path, required=True)
    score.add_argument("--pool", type=Path, required=True)
    score.add_argument("--judgments", type=Path, default=JUDGMENTS,
                       help="helper JSONL with query_id, candidate_id, judge_id, grade, status; adjudication needs adjudicated_status, adjudicated_grade, and adjudicator_id")
    score.add_argument("--packets", type=Path, default=None)
    score.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.command == "validate":
        rows, checksum = validate_queries(args.queries)
        print(json.dumps({"queries": len(rows), "sha256": checksum}))
    elif args.command == "freeze":
        print(json.dumps(freeze_queries(args.snapshot_id, args.queries, args.output), indent=2))
    elif args.command == "run":
        print(json.dumps(run_retrieval(args.snapshot_id, args.queries, args.freeze, args.output, args.split), indent=2))
    elif args.command == "pool":
        print(json.dumps(build_pool(args.run, args.queries, args.freeze, args.output, args.packets), indent=2))
    else:
        print(json.dumps(score_run(args.run, args.pool, args.judgments, args.output, args.packets), indent=2))


if __name__ == "__main__":
    main()
