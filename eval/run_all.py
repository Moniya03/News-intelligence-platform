"""Master evaluation runner for Multilingual News Intelligence Platform.

Executes all 5 evaluation benchmarks in sequence and outputs a formatted summary table.
"""

from __future__ import annotations

import logging
import sys
from eval.cluster_eval import run_cluster_eval
from eval.misinfo_eval import run_misinfo_eval
from eval.rag_eval import run_rag_eval
from eval.retrieval_flores import run_flores_eval
from eval.retrieval_news import run_news_retrieval_eval

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("eval.run_all")


def print_banner(title: str) -> None:
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def main() -> None:
    print_banner("RUNNING MULTILINGUAL NEWS INTELLIGENCE EVALUATION SUITE")

    # 1. FLORES-200 Retrieval
    print("\n[1/5] Evaluating Cross-Lingual Sentence Retrieval (FLORES-200)...")
    flores_res = run_flores_eval()

    # 2. News Retrieval Ablation
    print("\n[2/5] Evaluating News Retrieval Ablations (BM25 -> Dense -> Hybrid -> Reranker)...")
    news_res = run_news_retrieval_eval()

    # 3. RAG vs No-Retrieval
    print("\n[3/5] Evaluating End-to-End RAG Faithfulness & Citation Accuracy...")
    rag_res = run_rag_eval()

    # 4. Clustering Quality
    print("\n[4/5] Evaluating Topic & Event Clustering (NMI, ARI, Multilingual Purity)...")
    cluster_res = run_cluster_eval()

    # 5. Misinformation Detection
    print("\n[5/5] Evaluating Misinformation Detection & Cross-Source Agreement...")
    misinfo_res = run_misinfo_eval()

    # Summary Display
    print_banner("EVALUATION SUMMARY TABLE")

    print("\n1. FLORES-200 Cross-Lingual Retrieval (Recall@10)")
    print("-" * 65)
    print(f"{'Model':<30} | {'en->hi':<10} | {'en->bn':<10} | {'en->ta':<10}")
    print("-" * 65)
    for model_name, pairs in flores_res.get("models", {}).items():
        hi_r = pairs.get("en->hi", {}).get("Recall@10", 0.0)
        bn_r = pairs.get("en->bn", {}).get("Recall@10", 0.0)
        ta_r = pairs.get("en->ta", {}).get("Recall@10", 0.0)
        print(f"{model_name:<30} | {hi_r:<10.2f} | {bn_r:<10.2f} | {ta_r:<10.2f}")

    print("\n2. News Retrieval Ablation Benchmark")
    print("-" * 65)
    print(f"{'Retrieval Stage':<30} | {'Recall@5':<10} | {'MRR':<10} | {'nDCG@10':<10}")
    print("-" * 65)
    for stage, metrics in news_res.get("results", {}).items():
        r5 = metrics.get("Recall@5", 0.0)
        mrr = metrics.get("MRR", 0.0)
        ndcg = metrics.get("nDCG@10", 0.0)
        print(f"{stage:<30} | {r5:<10.2f} | {mrr:<10.2f} | {ndcg:<10.2f}")

    print("\n3. RAG vs No-Retrieval LLM Comparison")
    print("-" * 65)
    print(f"{'System':<35} | {'Faithful':<8} | {'Correct':<8} | {'Cit-Acc':<8}")
    print("-" * 65)
    for sys_name, metrics in rag_res.get("comparison", {}).items():
        f = metrics.get("faithfulness", 0.0)
        c = metrics.get("correctness", 0.0)
        ca = metrics.get("citation_accuracy", 0.0)
        print(f"{sys_name:<35} | {f:<8.2f} | {c:<8.2f} | {ca:<8.2f}")

    print("\n4. Clustering Quality (BERTopic vs TF-IDF Baseline)")
    print("-" * 65)
    print(f"{'Model':<35} | {'NMI':<8} | {'ARI':<8} | {'MultiLang %':<12}")
    print("-" * 65)
    for cl_model, metrics in cluster_res.get("models", {}).items():
        nmi = metrics.get("NMI", 0.0)
        ari = metrics.get("ARI", 0.0)
        purity = metrics.get("pct_clusters_multilingual", 0.0)
        print(f"{cl_model:<35} | {nmi:<8.2f} | {ari:<8.2f} | {purity:<12.1f}%")

    print("\n5. Misinformation Detection Benchmark")
    print("-" * 65)
    print(f"{'Variant':<45} | {'Macro-F1':<10}")
    print("-" * 65)
    for variant, metrics in misinfo_res.get("variants", {}).items():
        f1 = metrics.get("macro_f1", 0.0)
        print(f"{variant:<45} | {f1:<10.2f}")

    print("=" * 70)
    print("All evaluation artifacts written to results/*.json")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
