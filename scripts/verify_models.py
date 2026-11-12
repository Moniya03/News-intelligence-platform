"""Run one real embedding or reranking smoke test in a fresh process.

Run each component separately so the two model weights never compete for the
4 GB laptop GPU's memory at the same time.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import get_config


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=("embedder", "reranker"))
    parser.add_argument("--device", choices=("cuda", "cpu"))
    args = parser.parse_args()

    config = get_config().get("models", {})
    device = args.device or config.get("device", "cpu")
    fp16 = bool(config.get("fp16", False))
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but torch.cuda.is_available() is false")

    started = time.perf_counter()
    if args.component == "embedder":
        from core.embed import EmbedModel

        model_name = config.get("embedder", "BAAI/bge-m3")
        model = EmbedModel(model_name=model_name, fp16=fp16, device=device)
        if model.backend != "flagembedding" or (device == "cuda" and model.device != "cuda"):
            raise SystemExit(f"real FlagEmbedding backend unavailable: {model.backend}")
        output = model.embed_texts(
            ["भारत में मौसम की जानकारी", "Weather information in India"], batch_size=1
        )
        if output.shape != (2, 1024) or not torch.isfinite(torch.from_numpy(output)).all():
            raise SystemExit(f"invalid embedding output shape={output.shape}")
        details = {"dimension": output.shape[1], "vectors": output.shape[0], "finite": True}
    else:
        from core.rerank import RerankModel

        model_name = config.get("reranker", "BAAI/bge-reranker-v2-m3")
        model = RerankModel(model_name=model_name, fp16=fp16, device=device)
        if model.backend != "cross_encoder":
            raise SystemExit(f"real CrossEncoder backend unavailable: {model.backend}")
        results = model.rerank(
            "भारत में मौसम कैसा है?",
            [
                {"article_id": "smoke-hi", "text": "भारत में कई राज्यों में बारिश की संभावना है।", "score": 0.1},
                {"article_id": "smoke-en", "text": "Several regions may see rainfall today.", "score": 0.2},
            ],
            top_k=2,
        )
        scores = [float(item["score"]) for item in results]
        if len(scores) != 2 or not all(math.isfinite(score) for score in scores):
            raise SystemExit("invalid reranker output")
        details = {"scores": len(scores), "finite": True}

    if device == "cuda":
        torch.cuda.synchronize()
        details["gpu_allocated_mib"] = round(torch.cuda.memory_allocated() / 2**20, 1)
        details["gpu"] = torch.cuda.get_device_name(0)
    print(json.dumps({
        "status": "PASS",
        "component": args.component,
        "model": model_name,
        "backend": model.backend,
        "device": device,
        "fp16": fp16 and device == "cuda",
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        **details,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
