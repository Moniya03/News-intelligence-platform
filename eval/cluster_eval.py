"""Legacy clustering metrics; no validated frozen snapshot exists yet."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

RESULTS_PATH = Path("results/cluster_eval.json")


def load_articles_with_categories(mongo_client: Any = None, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load real labeled articles, refusing synthetic fallback samples."""
    if mongo_client is None or not db_name:
        raise RuntimeError("A corpus database is required; synthetic clustering samples are disabled.")
    docs = list(mongo_client[db_name]["articles"].find(
        {"category": {"$ne": None}},
        {"title": 1, "body": 1, "lang": 1, "category": 1, "cluster_id": 1},
    ))
    if len(docs) < 10:
        raise RuntimeError(f"Only {len(docs)} labeled articles found; refusing to score an undersized corpus.")
    return docs


def compute_multilingual_purity(cluster_labels: np.ndarray, langs: List[str]) -> float:
    """Calculate the percentage of non-singleton clusters with multiple languages."""
    unique_clusters = set(cluster_labels)
    multi_lang_count = 0
    valid_clusters = 0
    for cluster in unique_clusters:
        indices = np.where(cluster_labels == cluster)[0]
        if len(indices) <= 1:
            continue
        valid_clusters += 1
        if len({langs[index] for index in indices}) > 1:
            multi_lang_count += 1
    return round(multi_lang_count / max(1, valid_clusters) * 100.0, 2)


def run_cluster_eval(output_file: Path | str = RESULTS_PATH) -> Dict[str, Any]:
    """Disable the old benchmark until Slice 07 uses a frozen snapshot."""
    from eval import legacy_evaluation_disabled

    legacy_evaluation_disabled("Clustering evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate cross-lingual clustering.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Path to output json")
    args = parser.parse_args()
    run_cluster_eval(output_file=args.output)
