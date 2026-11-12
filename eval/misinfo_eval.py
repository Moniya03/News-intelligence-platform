"""Legacy misinformation benchmark, excluded from the project scope."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

RESULTS_PATH = Path("results/misinfo_eval.json")


def run_misinfo_eval(output_file: Path | str = RESULTS_PATH) -> Dict[str, Any]:
    """Do not score unsupported credibility or misinformation labels."""
    from eval import legacy_evaluation_disabled

    legacy_evaluation_disabled("Misinformation evaluation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate misinformation detection.")
    parser.add_argument("--output", default=str(RESULTS_PATH), help="Path to output json")
    args = parser.parse_args()
    run_misinfo_eval(output_file=args.output)
