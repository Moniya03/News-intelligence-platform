"""Legacy RAG evaluation entrypoint, disabled because its scores were fabricated."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

RESULTS_PATH = Path("results/rag_eval.json")


def run_rag_eval(output_file: Path | str = RESULTS_PATH) -> Dict[str, Any]:
    """Do not create metrics until judged held-out data and a real judge are available."""
    from eval import legacy_evaluation_disabled

    legacy_evaluation_disabled("RAG evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate RAG faithfulness and correctness.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Path to output json")
    args = parser.parse_args()
    run_rag_eval(output_file=args.output)
