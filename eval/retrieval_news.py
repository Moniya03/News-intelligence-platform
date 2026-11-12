"""Evaluation script: News retrieval ablation benchmark.

Evaluates BM25 -> dense -> hybrid -> hybrid+reranker ablation pipeline
on news queries using Recall@5, MRR, and nDCG@10.
Results are saved to results/retrieval_news.json.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from pymongo import MongoClient

from core.config import get_config
from core.embed import get_embed_model
from core.index import get_weaviate_client
from core.rerank import get_rerank_model
from core.retrieve import retrieve_bm25, retrieve_dense, retrieve_hybrid

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

RESULTS_PATH = Path("results/retrieval_news.json")

# Hand-crafted benchmark test queries with target relevant article identifiers

def load_eval_queries(mongo_client: Optional[MongoClient] = None, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load explicit relevance judgments; never substitute hand-written qrels."""
    if mongo_client is not None and db_name:
        docs = list(mongo_client[db_name]["eval_qa"].find({}))
        queries = [
            {
                "query_id": str(d.get("_id", d.get("query_id", ""))),
                "query": str(d.get("query", "")),
                "relevant_ids": [str(rid) for rid in d.get("relevant_ids", [])],
            }
            for d in docs
            if d.get("query") and d.get("relevant_ids")
        ]
        if queries:
            return queries
    raise RuntimeError("No explicit relevance judgments found in eval_qa; refusing to use fabricated benchmark queries.")


def compute_metrics(retrieved_ids: List[str], relevant_ids: List[str]) -> Dict[str, float]:
    """Calculate Recall@5, MRR, and nDCG@10 for a single query."""
    rel_set = set(relevant_ids)

    # 1. Recall@5
    top5 = retrieved_ids[:5]
    recall_5 = 1.0 if any(r in rel_set for r in top5) else 0.0

    # 2. MRR (Mean Reciprocal Rank)
    mrr = 0.0
    for rank, rid in enumerate(retrieved_ids, 1):
        if rid in rel_set:
            mrr = 1.0 / rank
            break

    # 3. nDCG@10
    top10 = retrieved_ids[:10]
    dcg = 0.0
    for rank, rid in enumerate(top10, 1):
        if rid in rel_set:
            dcg += 1.0 / math.log2(rank + 1)

    idcg = 0.0
    n_rel = min(10, len(rel_set))
    for rank in range(1, n_rel + 1):
        idcg += 1.0 / math.log2(rank + 1)

    ndcg_10 = (dcg / idcg) if idcg > 0 else 0.0

    return {
        "Recall@5": round(recall_5, 4),
        "MRR": round(mrr, 4),
        "nDCG@10": round(ndcg_10, 4),
    }


def run_news_retrieval_eval(output_file: Path | str = RESULTS_PATH) -> Dict[str, Any]:
    """Old benchmark lacked a valid corpus, query split, and stable relevance labels."""
    from eval import legacy_evaluation_disabled

    legacy_evaluation_disabled("News retrieval evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate news retrieval ablation.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Path to output json")
    args = parser.parse_args()

    run_news_retrieval_eval(output_file=args.output)
