"""Reproducible weak-label comparison for frozen-snapshot topic runs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


SNAPSHOT_ID = "corpus-59b2b589fe3bbdbffdc3"
CATEGORIES = ("politics", "finance", "health", "science_technology", "environment", "sports")
SEED = 42
VECTORIZER_SETTINGS = {"analyzer": "char", "ngram_range": [2, 5], "min_df": 2, "max_features": 200_000, "sublinear_tf": True, "dtype": "float32"}
KMEANS_SETTINGS = {"n_clusters": 6, "init": "k-means++", "n_init": 10, "max_iter": 300, "random_state": SEED, "algorithm": "lloyd"}
ROOT = Path("data/topic_runs")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _purity(truth: list[str], predicted: list[int]) -> float | None:
    if not truth:
        return None
    clusters: dict[int, Counter[str]] = defaultdict(Counter)
    for label, cluster in zip(truth, predicted, strict=True):
        clusters[cluster][label] += 1
    return sum(max(counts.values()) for counts in clusters.values()) / len(truth)


def _scores(truth: list[str], predicted: list[int]) -> dict[str, float | int | None]:
    if len(truth) != len(predicted):
        raise ValueError("truth/prediction denominator mismatch")
    if len(truth) < 2 or len(set(truth)) < 2:
        return {"n": len(truth), "nmi": None, "ari": None, "purity": _purity(truth, predicted)}
    return {
        "n": len(truth),
        "nmi": float(normalized_mutual_info_score(truth, predicted)),
        "ari": float(adjusted_rand_score(truth, predicted)),
        "purity": _purity(truth, predicted),
    }


def _metrics(articles: list[dict[str, Any]], predicted: list[int]) -> dict[str, Any]:
    eligible = [(i, str(a.get("category", ""))) for i, a in enumerate(articles) if a.get("category") in CATEGORIES]
    out: dict[str, Any] = {
        "eligible_category_articles": len(eligible),
        "unmapped_articles_excluded": len(articles) - len(eligible),
        "articles_with_multiple_publisher_categories": sum(len(a.get("categories", [])) > 1 for a in articles),
        "category_counts": {category: sum(label == category for _, label in eligible) for category in CATEGORIES},
        "unmapped_category_values": dict(sorted(Counter(str(a.get("category", "unknown")) for a in articles if a.get("category") not in CATEGORIES).items())),
        "all_document_denominator": len(articles),
        "overall": _scores([label for _, label in eligible], [int(predicted[i]) for i, _ in eligible]),
        "by_language": {},
        "label_scope": "single primary publisher-section category; weak proxy, not verified topic truth",
    }
    for lang in sorted({str(a.get("lang", "unknown")) for a in articles}):
        selected = [(i, label) for i, label in eligible if articles[i].get("lang") == lang]
        out["by_language"][lang] = _scores([label for _, label in selected], [int(predicted[i]) for i, _ in selected])
    return out


def _concentration(articles: list[dict[str, Any]], predicted: list[int]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for cluster in sorted(set(map(int, predicted))):
        ids = [i for i, value in enumerate(predicted) if int(value) == cluster]
        rows[str(cluster)] = {
            "size": len(ids),
            "languages": dict(sorted(Counter(str(articles[i].get("lang", "unknown")) for i in ids).items())),
            "publishers": dict(sorted(Counter(str(articles[i].get("source_adapter", "unknown")) for i in ids).items())),
            "exact_duplicate_articles": sum(bool(articles[i].get("duplicate_group_id")) for i in ids),
            "exact_duplicate_groups": len({articles[i]["duplicate_group_id"] for i in ids if articles[i].get("duplicate_group_id")}),
        }
    return rows


def _duplicate_summary(articles: list[dict[str, Any]]) -> dict[str, Any]:
    groups = Counter(a["duplicate_group_id"] for a in articles if a.get("duplicate_group_id"))
    return {
        "exact_duplicate_groups": len(groups),
        "exact_duplicate_articles": sum(groups.values()),
        "near_duplicate_or_syndication_check": "not performed; exact normalized-body groups only",
    }


def _require_provenance(artifact: dict[str, Any], provenance: dict[str, Any], keys: dict[str, str]) -> None:
    if any(artifact.get(artifact_key) != provenance[provenance_key] for artifact_key, provenance_key in keys.items()):
        raise ValueError("comparison artifact checksums differ from verified snapshot provenance")


def run_baseline(snapshot_id: str = SNAPSHOT_ID) -> tuple[Path, dict[str, Any], list[dict[str, Any]]]:
    from core.snapshot_topics import load_snapshot_topic_inputs

    manifest, articles, article_ids, _, provenance = load_snapshot_topic_inputs(snapshot_id)
    if not articles or len(articles) != len(article_ids) or len(set(article_ids)) != len(article_ids):
        raise ValueError("snapshot loader returned empty or misaligned articles")
    if manifest.get("snapshot_id") != snapshot_id:
        raise ValueError("snapshot loader returned a different snapshot")
    texts = [f"{a.get('title', '')}\n{a.get('body', '')}" for a in articles]
    vectorizer = TfidfVectorizer(**{**VECTORIZER_SETTINGS, "ngram_range": tuple(VECTORIZER_SETTINGS["ngram_range"]), "dtype": np.float32})
    matrix = vectorizer.fit_transform(texts)
    if matrix.shape[1] == 0:
        raise ValueError("snapshot produced no character n-gram features")
    assignment = KMeans(**KMEANS_SETTINGS).fit_predict(matrix)
    repeat = KMeans(**KMEANS_SETTINGS).fit_predict(matrix)
    if not np.array_equal(assignment, repeat):
        raise AssertionError("fixed-seed KMeans assignments were not reproducible")

    ids_sha = _sha(_canonical_bytes(article_ids))
    settings = {"vectorizer": VECTORIZER_SETTINGS, "kmeans": KMEANS_SETTINGS, "text_fields": ["title", "body"]}
    settings_sha = _sha(_json_bytes(settings))[:16]
    run_id = f"tfidf-kmeans-{settings_sha}-{ids_sha[:12]}"
    baseline = [int(value) for value in assignment]
    docs = [
        {"article_id": article_id, "cluster_id": baseline[i], "category": articles[i].get("category"), "lang": articles[i].get("lang"), "source_adapter": articles[i].get("source_adapter"), "duplicate_group_id": articles[i].get("duplicate_group_id")}
        for i, article_id in enumerate(article_ids)
    ]
    vocabulary_sha = _sha(_json_bytes(vectorizer.get_feature_names_out().tolist()))
    artifact = {
        "schema_version": 1,
        "algorithm": "tfidf-kmeans",
        "run_id": run_id,
        "snapshot_id": snapshot_id,
        "manifest_sha256": provenance["manifest_sha256"],
        "articles_sha256": provenance["articles_sha256"],
        "chunks_sha256": provenance["chunks_sha256"],
        "embeddings_sha256": provenance["embeddings_sha256"],
        "article_ids_sha256": ids_sha,
        "settings": settings,
        "settings_sha256": settings_sha,
        "seed": SEED,
        "versions": {name: importlib.metadata.version(name) for name in ("scikit-learn", "numpy")},
        "input_articles": len(articles),
        "input_feature_count": int(matrix.shape[1]),
        "vocabulary_sha256": vocabulary_sha,
        "actual_cluster_count": len(set(baseline)),
        "assignments": docs,
        "metrics": _metrics(articles, baseline),
        "concentration": _concentration(articles, baseline),
        "duplicate_overlap": _duplicate_summary(articles),
        "repeatability_check": "passed: second fit on the same frozen inputs produced identical assignments",
    }
    folder = ROOT / snapshot_id / "baseline" / run_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "baseline.json"
    payload = _json_bytes(artifact)
    if target.exists() and target.read_bytes() != payload:
        raise ValueError(f"refusing to replace different baseline artifact: {target}")
    if not target.exists():
        target.write_bytes(payload)
    return target, artifact, articles


def compare_with_topics(snapshot_id: str = SNAPSHOT_ID, baseline_path: Path | None = None) -> Path:
    from core.snapshot_topics import load_active_topic_run, load_snapshot_topic_inputs

    manifest, articles, article_ids, _, provenance = load_snapshot_topic_inputs(snapshot_id)
    if manifest.get("snapshot_id") != snapshot_id or len(articles) != len(article_ids):
        raise ValueError("snapshot inputs are inconsistent")
    if baseline_path is None:
        candidates = sorted((ROOT / snapshot_id / "baseline").glob("*/baseline.json"))
        if len(candidates) != 1:
            raise ValueError(f"expected exactly one baseline artifact, found {len(candidates)}")
        baseline_path = candidates[0]
    baseline = json.loads(baseline_path.read_text())
    active = json.loads((ROOT / "active.json").read_text())
    if active.get("snapshot_id") != snapshot_id:
        raise ValueError("active BERTopic run points to a different snapshot")
    topic, _ = load_active_topic_run(snapshot_id, article_ids)
    topic_path = ROOT / snapshot_id / str(active["settings_hash"]) / str(active["run_id"]) / "topic_run.json"
    for artifact in (baseline, topic):
        if artifact.get("snapshot_id") != snapshot_id or artifact.get("article_ids_sha256") != _sha(_canonical_bytes(article_ids)):
            raise ValueError("comparison artifacts do not match frozen snapshot article identity/order")
    _require_provenance(baseline, provenance, {
        "manifest_sha256": "manifest_sha256", "articles_sha256": "articles_sha256",
        "chunks_sha256": "chunks_sha256", "embeddings_sha256": "embeddings_sha256",
    })
    if topic.get("provenance") != provenance:
        raise ValueError("BERTopic provenance differs from verified snapshot")
    _require_provenance(topic, provenance, {"snapshot_manifest_sha256": "manifest_sha256"})
    baseline_rows = baseline.get("assignments", [])
    if [row.get("article_id") for row in baseline_rows] != article_ids:
        raise ValueError("baseline assignment order differs from snapshot")
    bt = [int(row["cluster_id"]) for row in baseline_rows]
    topic_ids = topic.get("article_ids", [])
    memberships = topic.get("memberships", {})
    if topic_ids != article_ids or set(memberships) != set(article_ids):
        raise ValueError("BERTopic assignment order differs from snapshot")
    tt = [int(memberships[article_id]) for article_id in article_ids]
    noise = [i for i, value in enumerate(tt) if value == -1]
    assigned = [i for i, value in enumerate(tt) if value != -1]
    topic_all = _metrics(articles, tt)
    topic_all["noise_articles"] = len(noise)
    topic_all["noise_rate"] = len(noise) / len(tt) if tt else None
    topic_all["noise_policy"] = "all-document metrics include -1 as one explicit noise assignment"
    topic_assigned = _metrics([articles[i] for i in assigned], [tt[i] for i in assigned])
    topic_assigned["assigned_articles"] = len(assigned)
    topic_assigned["excluded_noise_articles"] = len(noise)
    results = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "manifest_sha256": provenance["manifest_sha256"],
        "article_ids_sha256": _sha(_canonical_bytes(article_ids)),
        "baseline_run_id": baseline["run_id"],
        "baseline_artifact_sha256": _sha(baseline_path.read_bytes()),
        "bertopic_run_id": topic["run_id"],
        "bertopic_artifact_sha256": _sha(topic_path.read_bytes()),
        "comparison": {
            "weak_label_warning": "publisher section categories are coarse weak labels; agreement does not establish event coherence, truth, or fact verification",
            "baseline": {"algorithm": baseline["algorithm"], "actual_clusters": baseline["actual_cluster_count"], "metrics": baseline["metrics"], "concentration": baseline["concentration"]},
            "bertopic": {"algorithm": topic["algorithm"], "actual_clusters": topic.get("topic_count", topic.get("actual_cluster_count")), "noise_articles": len(noise), "noise_rate": topic_all["noise_rate"], "all_document_metrics": topic_all, "assigned_document_metrics": topic_assigned, "concentration": _concentration(articles, tt)},
            "duplicate_overlap": {"baseline": baseline["duplicate_overlap"], "bertopic": _duplicate_summary(articles)},
        },
    }
    folder = baseline_path.parent
    output = folder / f"comparison-{topic['run_id']}.json"
    payload = _json_bytes(results)
    if output.exists() and output.read_bytes() != payload:
        raise ValueError(f"refusing to replace different comparison artifact: {output}")
    if not output.exists():
        output.write_bytes(payload)
    return output


def _self_check() -> None:
    assert _purity(["a", "b", "b"], [0, 0, 1]) == 2 / 3
    assert _scores(["a"], [0])["nmi"] is None
    assert _scores(["a", "b"], [-1, 0])["n"] == 2
    try:
        _require_provenance({"embeddings_sha256": "stale"}, {"embeddings_sha256": "current"}, {"embeddings_sha256": "embeddings_sha256"})
    except ValueError:
        pass
    else:
        raise AssertionError("stale artifact provenance was accepted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-id", default=SNAPSHOT_ID)
    parser.add_argument("--baseline-only", action="store_true", help="save reproducible TF-IDF/KMeans artifact")
    parser.add_argument("--compare", action="store_true", help="compare an existing baseline with the BERTopic run")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        _self_check()
        print("snapshot topic metric checks passed")
        return
    if args.baseline_only or not args.compare:
        path, artifact, _ = run_baseline(args.snapshot_id)
        print(json.dumps({"baseline": str(path), "run_id": artifact["run_id"], "clusters": artifact["actual_cluster_count"], "metrics": artifact["metrics"]}, indent=2))
    if args.compare:
        print(compare_with_topics(args.snapshot_id))


if __name__ == "__main__":
    main()
