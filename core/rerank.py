"""Cross-encoder reranker module for Multilingual News Intelligence Platform.

Reranks candidate chunks using BAAI/bge-reranker-v2-m3 cross-encoder and
deduplicates citations across articles and near-identical passages.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from core.config import get_config
from core.dedupe import dedup_citations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class RerankModel:
    """Cross-encoder reranking wrapper for candidate chunk rescoring."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        fp16: bool = True,
        device: str = "cuda",
    ):
        """Initialize reranking cross-encoder model.

        Args:
            model_name: HuggingFace model identifier.
            fp16: Whether to use half-precision.
            device: Target device ('cuda' or 'cpu').
        """
        self.model_name = model_name
        self.fp16 = fp16
        self.device = device
        self._model = None
        self.backend = "fallback"

        self._init_model()

    def _init_model(self) -> None:
        """Attempt to load CrossEncoder with sentence_transformers."""
        try:
            import torch
            from sentence_transformers import CrossEncoder  # type: ignore

            resolved_device = "cuda" if (self.device == "cuda" and torch.cuda.is_available()) else "cpu"
            logger.info("Loading CrossEncoder '%s' on %s...", self.model_name, resolved_device)
            # CrossEncoder supports model_kwargs or torch_dtype
            self._model = CrossEncoder(self.model_name, device=resolved_device)
            if self.fp16 and resolved_device == "cuda" and hasattr(self._model.model, "half"):
                self._model.model.half()
            self.backend = "cross_encoder"
            logger.info("Loaded CrossEncoder successfully.")
        except Exception as e:
            logger.warning("Could not load CrossEncoder (%s). Using lexical fallback reranker.", e)
            self.backend = "fallback"

    def _lexical_score(self, query: str, text: str, initial_score: float) -> float:
        """Compute fallback relevance score using token overlap and initial score."""
        q_tokens = set(query.lower().split())
        t_tokens = set(text.lower().split())
        if not q_tokens or not t_tokens:
            return float(initial_score)

        overlap = len(q_tokens.intersection(t_tokens)) / len(q_tokens)
        return float(initial_score * 0.5 + overlap * 0.5)

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 8,
        dedup_threshold: float = 0.95,
    ) -> List[Dict[str, Any]]:
        """Rerank candidates using cross-encoder and deduplicate citations.

        Args:
            query: The user query string.
            candidates: List of candidate chunk dictionaries.
            top_k: Number of chunks to retain after reranking and deduplication.
            dedup_threshold: Similarity cutoff for near-duplicate removal.

        Returns:
            List of top reranked and deduplicated chunks.
        """
        if not candidates:
            return []

        if len(candidates) <= 1:
            return candidates[:top_k]

        rescored_candidates: List[Dict[str, Any]] = []

        if self.backend == "cross_encoder" and self._model is not None:
            try:
                pairs = [[query, c.get("text", "")] for c in candidates]
                scores = self._model.predict(pairs)
                for cand, score in zip(candidates, scores):
                    item = dict(cand)
                    item["score"] = float(score)
                    rescored_candidates.append(item)
            except Exception as e:
                logger.error("Error during cross-encoder predict: %s. Using fallback.", e)
                self.backend = "fallback"

        if self.backend == "fallback" or not rescored_candidates:
            for cand in candidates:
                item = dict(cand)
                init_score = float(item.get("score", 0.5))
                text = item.get("text", "")
                item["score"] = self._lexical_score(query, text, init_score)
                rescored_candidates.append(item)

        # Sort by rerank score descending
        rescored_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # Apply deduplication (one chunk per article_id + text similarity filter)
        deduped = dedup_citations(rescored_candidates, sim_threshold=dedup_threshold)

        return deduped[:top_k]


_GLOBAL_RERANK_MODEL: Optional[RerankModel] = None


def get_rerank_model() -> RerankModel:
    """Return cached singleton instance of RerankModel configured from default.yaml."""
    global _GLOBAL_RERANK_MODEL
    if _GLOBAL_RERANK_MODEL is None:
        cfg = get_config()
        m_cfg = cfg.get("models", {})
        _GLOBAL_RERANK_MODEL = RerankModel(
            model_name=m_cfg.get("reranker", "BAAI/bge-reranker-v2-m3"),
            fp16=m_cfg.get("fp16", True),
            device=m_cfg.get("device", "cuda"),
        )
    return _GLOBAL_RERANK_MODEL
