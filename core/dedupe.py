"""Deduplication module for News Intelligence Platform.

Provides exact duplicate detection (SHA-256 over normalized text) and near-duplicate
filtering via cosine similarity over embedding vectors or text shingles.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Dict, List, Set
import numpy as np

logger = logging.getLogger(__name__)


def exact_hash(text: str) -> str:
    """Compute SHA256 hash of normalized text (lowercase, whitespace-stripped).

    Args:
        text: Input string.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    if not text:
        return hashlib.sha256(b"").hexdigest()
    # Normalize unicode / whitespace: collapse consecutive whitespace, strip, lowercase
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def remove_exact_duplicates(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove exact duplicate articles based on normalized title + body.

    Args:
        articles: List of article dictionaries with 'title' and 'body' keys.

    Returns:
        List of unique articles preserving first occurrence order.
    """
    seen_hashes: Set[str] = set()
    unique_articles: List[Dict[str, Any]] = []

    for art in articles:
        title = art.get("title", "") or ""
        body = art.get("body", "") or ""
        content_hash = exact_hash(f"{title} {body}")

        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)
        unique_articles.append(art)

    removed_count = len(articles) - len(unique_articles)
    if removed_count > 0:
        logger.info("Removed %d exact duplicate articles out of %d", removed_count, len(articles))

    return unique_articles


def remove_near_duplicates(embeddings: np.ndarray, threshold: float = 0.95) -> List[int]:
    """Identify indices of items to keep after filtering near-duplicates.

    Greedily keeps items whose cosine similarity to any previously kept item
    is strictly below the specified threshold.

    Args:
        embeddings: Array of shape (N, D) representing normalized or unnormalized vectors.
        threshold: Cosine similarity cutoff above which items are considered duplicates (default 0.95).

    Returns:
        List of integer indices to keep.
    """
    if embeddings is None or len(embeddings) == 0:
        return []

    n = len(embeddings)
    if n == 1:
        return [0]

    # Normalize vectors for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized_vecs = embeddings / norms

    kept_indices: List[int] = [0]
    kept_vectors = [normalized_vecs[0]]

    for i in range(1, n):
        candidate_vec = normalized_vecs[i]
        # Dot product with all already kept vectors
        sims = np.dot(kept_vectors, candidate_vec)
        if np.max(sims) < threshold:
            kept_indices.append(i)
            kept_vectors.append(candidate_vec)

    logger.debug(
        "Near-deduplication kept %d of %d items (threshold=%.2f)",
        len(kept_indices),
        n,
        threshold,
    )
    return kept_indices


def _jaccard_similarity(text1: str, text2: str, n_gram: int = 3) -> float:
    """Compute character n-gram Jaccard similarity between two texts."""
    s1 = set(text1[i : i + n_gram] for i in range(len(text1) - n_gram + 1))
    s2 = set(text2[i : i + n_gram] for i in range(len(text2) - n_gram + 1))
    if not s1 or not s2:
        return 0.0
    intersection = len(s1.intersection(s2))
    union = len(s1.union(s2))
    return intersection / union if union > 0 else 0.0


def dedup_citations(chunks: List[Dict[str, Any]], sim_threshold: float = 0.95) -> List[Dict[str, Any]]:
    """Deduplicate citation chunks for RAG.

    Ensures:
      1. At most one chunk per unique `article_id` (keeps highest scoring / first chunk).
      2. Chunks with near-identical text (similarity >= sim_threshold) are dropped.

    Args:
        chunks: List of chunk dictionaries with 'chunk_id', 'article_id', 'text', etc.
        sim_threshold: Cutoff for dropping near-identical texts (default 0.95).

    Returns:
        Filtered list of distinct chunk dictionaries.
    """
    if not chunks:
        return []

    # Step 1: Dedup by article_id (keep first/highest-scoring instance)
    seen_articles: Set[str] = set()
    article_deduped: List[Dict[str, Any]] = []

    for chunk in chunks:
        art_id = chunk.get("article_id")
        if art_id is not None and art_id in seen_articles:
            continue
        if art_id is not None:
            seen_articles.add(art_id)
        article_deduped.append(chunk)

    # Step 2: Drop near-identical texts among the survivors
    final_chunks: List[Dict[str, Any]] = []
    for chunk in article_deduped:
        text = chunk.get("text", "") or ""
        is_dup = False
        for accepted in final_chunks:
            accepted_text = accepted.get("text", "") or ""
            # Quick exact check
            if exact_hash(text) == exact_hash(accepted_text):
                is_dup = True
                break
            # Text similarity check
            if _jaccard_similarity(text.lower(), accepted_text.lower()) >= sim_threshold:
                is_dup = True
                break
        if not is_dup:
            final_chunks.append(chunk)

    return final_chunks
