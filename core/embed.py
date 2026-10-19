"""BGE-M3 embedding wrapper for Multilingual News Intelligence Platform.

Wraps FlagEmbedding's BGEM3FlagModel with GPU/fp16 support, singleton caching,
and fallback representation when GPU or heavy ML libraries are not available.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import pandas as pd

from core.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

EMBED_DIM = 1024


class EmbedModel:
    """Wrapper around BGE-M3 embedding model."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        fp16: bool = True,
        device: str = "cuda",
    ):
        """Initialize embedding model with fp16 and device configuration.

        Args:
            model_name: HuggingFace model identifier.
            fp16: Whether to use half-precision floating point.
            device: Target device ('cuda' or 'cpu').
        """
        self.model_name = model_name
        self.fp16 = fp16
        self.device = device
        self.backend = "fallback"
        self._model = None

        self._init_model()

    def _init_model(self) -> None:
        """Attempt to load FlagEmbedding BGEM3FlagModel, then SentenceTransformers, else fallback."""
        try:
            import torch
            resolved_device = "cuda" if (self.device == "cuda" and torch.cuda.is_available()) else "cpu"
            use_fp16 = self.fp16 and (resolved_device == "cuda")

            from FlagEmbedding import BGEM3FlagModel  # type: ignore
            logger.info("Loading FlagEmbedding '%s' on %s (fp16=%s)...", self.model_name, resolved_device, use_fp16)
            self._model = BGEM3FlagModel(
                self.model_name,
                use_fp16=use_fp16,
                device=resolved_device,
            )
            self.backend = "flagembedding"
            logger.info("Successfully loaded FlagEmbedding BGEM3FlagModel.")
            return
        except Exception as e:
            logger.warning("FlagEmbedding unavailable (%s). Checking alternative backends...", e)

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading SentenceTransformer for '%s'...", self.model_name)
            self._model = SentenceTransformer(self.model_name, device=self.device)
            self.backend = "sentence_transformers"
            logger.info("Successfully loaded SentenceTransformer.")
            return
        except Exception as e:
            logger.warning("SentenceTransformer unavailable (%s). Using deterministic mock embedder.", e)
            self.backend = "fallback"

    def _deterministic_embed(self, text: str) -> np.ndarray:
        """Generate a deterministic 1024-dim unit vector from text for development/fallback."""
        if not text:
            vec = np.zeros(EMBED_DIM, dtype=np.float32)
            vec[0] = 1.0
            return vec

        # Seed random generator with SHA256 of text
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="big") % (2**32)
        rng = np.random.RandomState(seed)
        vec = rng.randn(EMBED_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of texts into dense vectors of shape (len(texts), 1024).

        Args:
            texts: List of text strings.
            batch_size: Batch size for inference.

        Returns:
            np.ndarray: Matrix of shape (N, 1024) with float32 values.
        """
        if not texts:
            return np.empty((0, EMBED_DIM), dtype=np.float32)

        if self.backend == "flagembedding":
            output = self._model.encode(
                texts,
                batch_size=batch_size,
                max_length=8192,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            dense = output["dense_vecs"]
            if isinstance(dense, list):
                dense = np.array(dense, dtype=np.float32)
            return dense.astype(np.float32)

        elif self.backend == "sentence_transformers":
            vecs = self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)
            return np.array(vecs, dtype=np.float32)

        else:
            # Deterministic fallback
            vectors = [self._deterministic_embed(t) for t in texts]
            return np.array(vectors, dtype=np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query into a 1D vector of shape (1024,).

        Args:
            text: Query string.

        Returns:
            np.ndarray: 1D vector of shape (1024,) with float32 values.
        """
        matrix = self.embed_texts([text], batch_size=1)
        return matrix[0]


# Singleton instance
_GLOBAL_EMBED_MODEL: Optional[EmbedModel] = None


def get_embed_model() -> EmbedModel:
    """Return cached singleton instance of EmbedModel configured from default.yaml."""
    global _GLOBAL_EMBED_MODEL
    if _GLOBAL_EMBED_MODEL is None:
        cfg = get_config()
        m_cfg = cfg.get("models", {})
        _GLOBAL_EMBED_MODEL = EmbedModel(
            model_name=m_cfg.get("embedder", "BAAI/bge-m3"),
            fp16=m_cfg.get("fp16", True),
            device=m_cfg.get("device", "cuda"),
        )
    return _GLOBAL_EMBED_MODEL


def embed_corpus(
    chunks_file: str | Path = "data/chunks.parquet",
    output_vectors: str | Path = "data/vectors.npy",
    batch_size: int = 32,
) -> np.ndarray:
    """Batch embed text chunks from parquet file and save to numpy array.

    Args:
        chunks_file: Path to input parquet file containing 'text' column.
        output_vectors: Destination path for .npy vectors file.
        batch_size: Batch size for embedding.

    Returns:
        np.ndarray: Embedded vectors.
    """
    path = Path(chunks_file)
    if not path.is_file():
        logger.warning("Chunks file not found: %s. Returning empty vectors.", path)
        return np.empty((0, EMBED_DIM), dtype=np.float32)

    df = pd.read_parquet(path)
    if "text" not in df.columns:
        raise ValueError(f"Missing 'text' column in {chunks_file}")

    texts = df["text"].fillna("").astype(str).tolist()
    logger.info("Embedding %d chunks with batch_size=%d...", len(texts), batch_size)

    embedder = get_embed_model()
    vectors = embedder.embed_texts(texts, batch_size=batch_size)

    out_path = Path(output_vectors)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(out_path, vectors)
    logger.info("Saved %d vectors (shape %s) to %s", len(vectors), vectors.shape, out_path)
    return vectors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch embed chunks.")
    parser.add_argument("--chunks", default="data/chunks.parquet", help="Path to chunks parquet")
    parser.add_argument("--output", default="data/vectors.npy", help="Output path for vectors.npy")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    args = parser.parse_args()

    embed_corpus(chunks_file=args.chunks, output_vectors=args.output, batch_size=args.batch_size)
