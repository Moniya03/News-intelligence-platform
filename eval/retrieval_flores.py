"""Legacy FLORES helpers; the previous runner used synthetic translations and scores."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

RESULTS_PATH = Path("results/retrieval_flores.json")


def load_flores_data(data_dir: Path | str = "data/flores200") -> Dict[str, List[str]]:
    """Load aligned real data for the four project languages."""
    path = Path(data_dir)
    data = {}
    for lang in ["en", "hi", "bn", "mr"]:
        lang_file = path / f"devtest.{lang}"
        if not lang_file.is_file():
            raise FileNotFoundError(f"Missing real FLORES devtest file: {lang_file}")
        with lang_file.open(encoding="utf-8") as f:
            data[lang] = [line.strip() for line in f if line.strip()]
    lengths = {len(sentences) for sentences in data.values()}
    if len(lengths) != 1 or not lengths or 0 in lengths:
        raise ValueError("FLORES language files must contain aligned, non-empty sentence rows")
    return data


def compute_recall_at_k(similarity_matrix: np.ndarray, ks: List[int] = [1, 10]) -> Dict[str, float]:
    """Compute Recall@k where the parallel sentence has the same row index."""
    n = similarity_matrix.shape[0]
    recalls = {}
    for k in ks:
        actual_k = min(k, similarity_matrix.shape[1])
        top_indices = np.argsort(similarity_matrix, axis=1)[:, ::-1][:, :actual_k]
        hits = sum(i in top_indices[i] for i in range(n))
        recalls[f"Recall@{k}"] = round(hits / n, 4) if n > 0 else 0.0
    return recalls


def eval_bm25_retrieval(source_texts: List[str], target_texts: List[str]) -> Dict[str, float]:
    """Legacy lexical overlap helper; not a suitable cross-lingual baseline."""
    n = len(source_texts)
    sim_matrix = np.zeros((n, len(target_texts)))
    for i, source in enumerate(source_texts):
        source_tokens = set(source.lower().split())
        for j, target in enumerate(target_texts):
            target_tokens = set(target.lower().split())
            sim_matrix[i, j] = len(source_tokens & target_tokens) / max(1, len(source_tokens))
    return compute_recall_at_k(sim_matrix, ks=[1, 10])


def run_flores_eval(output_file: Path | str = RESULTS_PATH) -> Dict[str, Any]:
    """Disable the old benchmark until a valid experiment is designed."""
    from eval import legacy_evaluation_disabled

    legacy_evaluation_disabled("FLORES evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate cross-lingual retrieval on FLORES-200.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Path to output json")
    args = parser.parse_args()
    run_flores_eval(output_file=args.output)
