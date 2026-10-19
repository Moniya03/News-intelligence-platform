"""Topic and event clustering module for Multilingual News Intelligence Platform.

Performs document clustering over BGE-M3 embeddings using BERTopic (UMAP + HDBSCAN)
or scikit-learn fallback, saves cluster documents and article assignments in MongoDB,
and serves cluster queries.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from sklearn.feature_extraction.text import TfidfVectorizer

from core.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _extract_top_terms_tfidf(texts: List[str], top_n: int = 5) -> List[str]:
    """Extract representative top terms from a list of texts using TF-IDF."""
    if not texts or all(not t.strip() for t in texts):
        return ["news", "report", "update"]
    try:
        tfidf = TfidfVectorizer(max_features=1000, stop_words="english", ngram_range=(1, 2))
        matrix = tfidf.fit_transform(texts)
        scores = np.asarray(matrix.sum(axis=0)).ravel()
        words = np.array(tfidf.get_feature_names_out())
        top_indices = np.argsort(scores)[::-1][:top_n]
        return words[top_indices].tolist()
    except Exception:
        # Fallback simple frequency count
        words = [w.lower() for t in texts for w in t.split() if len(w) > 3]
        from collections import Counter
        return [w for w, _ in Counter(words).most_common(top_n)] or ["topic"]


def run_clustering(
    embeddings_npy: str | Path = "data/vectors.npy",
    article_ids: Optional[List[str]] = None,
    mongo_client: Optional[Any] = None,
    db_name: Optional[str] = None,
    n_components: int = 5,
    min_cluster_size: int = 15,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Run clustering pipeline over embeddings and write assignments to MongoDB.

    Args:
        embeddings_npy: Path to dense vectors npy file.
        article_ids: Optional list of article IDs corresponding to vectors.
        mongo_client: MongoDB client instance.
        db_name: MongoDB database name.
        n_components: UMAP dimensionality reduction target components.
        min_cluster_size: Minimum cluster size for HDBSCAN.
        seed: Random state seed.

    Returns:
        List of cluster summary dictionaries.
    """
    cfg = get_config()
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    mongo_uri = cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")

    # Load vectors
    vec_path = Path(embeddings_npy)
    if not vec_path.is_file():
        logger.warning("Embeddings file %s not found. Skipping clustering.", vec_path)
        return []

    embeddings = np.load(vec_path)
    n_samples = len(embeddings)
    if n_samples == 0:
        logger.warning("Empty embeddings array. Skipping clustering.")
        return []

    # Connect to MongoDB
    client = mongo_client
    if client is None:
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
        except Exception as e:
            logger.warning("MongoDB not accessible (%s): %s", mongo_uri, e)
            client = None

    articles_coll = client[db_name]["articles"] if client is not None else None
    clusters_coll = client[db_name]["clusters"] if client is not None else None

    # Fetch articles if article_ids not provided
    articles_data: List[Dict[str, Any]] = []
    if articles_coll is not None:
        articles_data = list(articles_coll.find({}, {"_id": 1, "title": 1, "body": 1, "lang": 1}))

    if not article_ids:
        if articles_data:
            article_ids = [str(a["_id"]) for a in articles_data[:n_samples]]
        else:
            article_ids = [f"art_{i:06d}" for i in range(n_samples)]

    cluster_labels: np.ndarray

    # Try BERTopic
    bertopic_success = False
    try:
        from bertopic import BERTopic  # type: ignore
        import umap  # type: ignore
        import hdbscan  # type: ignore

        logger.info("Running BERTopic clustering with UMAP (n_components=%d) and HDBSCAN...", n_components)
        umap_model = umap.UMAP(n_components=n_components, random_state=seed, metric="cosine")
        hdbscan_model = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean", prediction_data=True)
        topic_model = BERTopic(umap_model=umap_model, hdbscan_model=hdbscan_model)

        titles = [a.get("title", "") for a in articles_data] if articles_data else [f"Doc {i}" for i in range(n_samples)]
        topics, _ = topic_model.fit_transform(titles[:n_samples], embeddings)
        cluster_labels = np.array(topics)
        bertopic_success = True
    except Exception as e:
        logger.warning("BERTopic clustering unavailable (%s). Falling back to KMeans.", e)

    if not bertopic_success:
        from sklearn.cluster import KMeans

        k = max(2, min(n_samples // min_cluster_size, 10))
        logger.info("Running KMeans clustering with k=%d...", k)
        kmeans = KMeans(n_clusters=k, random_state=seed, n_init="auto")
        cluster_labels = kmeans.fit_predict(embeddings)

    # Build cluster summaries
    unique_labels = sorted(set(cluster_labels))
    cluster_docs: List[Dict[str, Any]] = []

    # Map article_id -> article metadata
    art_meta = {str(a["_id"]): a for a in articles_data}

    for label in unique_labels:
        indices = np.where(cluster_labels == label)[0]
        member_ids = [article_ids[idx] for idx in indices if idx < len(article_ids)]
        size = len(member_ids)

        lang_counts = {"en": 0, "hi": 0, "bn": 0, "ta": 0}
        member_texts: List[str] = []

        for aid in member_ids:
            a = art_meta.get(aid, {})
            l = a.get("lang", "en").lower()
            if l in lang_counts:
                lang_counts[l] += 1
            else:
                lang_counts["en"] += 1
            title_text = f"{a.get('title', '')} {a.get('body', '')[:200]}"
            if title_text.strip():
                member_texts.append(title_text)

        top_terms = _extract_top_terms_tfidf(member_texts, top_n=5)
        label_name = f"Cluster {label}: " + ", ".join(top_terms[:3])

        cluster_doc = {
            "id": int(label),
            "label": label_name,
            "size": int(size),
            "lang_counts": lang_counts,
            "top_terms": top_terms,
        }
        cluster_docs.append(cluster_doc)

    # Write to MongoDB
    if client is not None and articles_coll is not None and clusters_coll is not None:
        try:
            # Update articles with cluster_id
            for aid, cl_id in zip(article_ids, cluster_labels):
                articles_coll.update_one({"_id": aid}, {"$set": {"cluster_id": int(cl_id)}})

            # Save cluster docs
            clusters_coll.delete_many({})
            for c_doc in cluster_docs:
                db_doc = dict(c_doc)
                db_doc["_id"] = c_doc["id"]
                clusters_coll.replace_one({"_id": c_doc["id"]}, db_doc, upsert=True)

            logger.info("Successfully updated MongoDB with %d clusters.", len(cluster_docs))
        except Exception as e:
            logger.error("Error writing clusters to MongoDB: %s", e)

    return cluster_docs


def get_clusters(mongo_client: Optional[Any] = None, db_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all cluster summaries from MongoDB.

    Args:
        mongo_client: Optional MongoClient instance.
        db_name: Database name.

    Returns:
        List of Cluster dicts: [{id, label, size, lang_counts, top_terms}].
    """
    cfg = get_config()
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    mongo_uri = cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")

    client = mongo_client
    close_client = False
    if client is None:
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            close_client = True
        except Exception as e:
            logger.warning("MongoDB unavailable for get_clusters (%s): %s", mongo_uri, e)
            return []

    try:
        db = client[db_name]
        docs = list(db["clusters"].find({}))
        results = []
        for d in docs:
            results.append({
                "id": int(d.get("id", d.get("_id", 0))),
                "label": str(d.get("label", "General Topic")),
                "size": int(d.get("size", 0)),
                "lang_counts": d.get("lang_counts", {"en": 0, "hi": 0, "bn": 0, "ta": 0}),
                "top_terms": d.get("top_terms", []),
            })
        return results
    except Exception as e:
        logger.error("Failed to query clusters from MongoDB: %s", e)
        return []
    finally:
        if close_client and client:
            client.close()


def get_cluster_articles(
    mongo_client: Optional[Any] = None,
    db_name: Optional[str] = None,
    cluster_id: int = 0,
    page: int = 1,
    limit: int = 20,
) -> Dict[str, Any]:
    """Retrieve paginated articles belonging to a specific cluster.

    Args:
        mongo_client: Optional MongoClient instance.
        db_name: Database name.
        cluster_id: Integer cluster identifier.
        page: 1-indexed page number.
        limit: Page size limit.

    Returns:
        Dict: {"articles": Article[], "total": number, "cluster": Cluster}.
    """
    cfg = get_config()
    db_name = db_name or cfg.get("mongo", {}).get("db", "news_intel")
    mongo_uri = cfg.get("mongo", {}).get("uri", "mongodb://localhost:27017")

    client = mongo_client
    close_client = False
    if client is None:
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            client.admin.command("ping")
            close_client = True
        except Exception as e:
            logger.warning("MongoDB unavailable for get_cluster_articles (%s): %s", mongo_uri, e)
            return {
                "articles": [],
                "total": 0,
                "cluster": {
                    "id": cluster_id,
                    "label": f"Cluster {cluster_id}",
                    "size": 0,
                    "lang_counts": {"en": 0, "hi": 0, "bn": 0, "ta": 0},
                    "top_terms": [],
                },
            }

    try:
        db = client[db_name]
        cluster_doc = db["clusters"].find_one({"$or": [{"_id": cluster_id}, {"id": cluster_id}]})
        if not cluster_doc:
            cluster_meta = {
                "id": cluster_id,
                "label": f"Cluster {cluster_id}",
                "size": 0,
                "lang_counts": {"en": 0, "hi": 0, "bn": 0, "ta": 0},
                "top_terms": [],
            }
        else:
            cluster_meta = {
                "id": int(cluster_doc.get("id", cluster_doc.get("_id", cluster_id))),
                "label": str(cluster_doc.get("label", f"Cluster {cluster_id}")),
                "size": int(cluster_doc.get("size", 0)),
                "lang_counts": cluster_doc.get("lang_counts", {"en": 0, "hi": 0, "bn": 0, "ta": 0}),
                "top_terms": cluster_doc.get("top_terms", []),
            }

        query = {"cluster_id": cluster_id}
        total = db["articles"].count_documents(query)
        skip = max(0, (page - 1) * limit)
        cursor = db["articles"].find(query).skip(skip).limit(limit)

        articles: List[Dict[str, Any]] = []
        for doc in cursor:
            articles.append({
                "article_id": str(doc.get("_id", doc.get("article_id", ""))),
                "title": str(doc.get("title", "")),
                "lang": str(doc.get("lang", "en")),
                "source": str(doc.get("source", "news")),
                "category": str(doc.get("category", "general")),
                "url": doc.get("url"),
            })

        return {
            "articles": articles,
            "total": total,
            "cluster": cluster_meta,
        }
    except Exception as e:
        logger.error("Error retrieving cluster articles from MongoDB: %s", e)
        return {
            "articles": [],
            "total": 0,
            "cluster": {
                "id": cluster_id,
                "label": f"Cluster {cluster_id}",
                "size": 0,
                "lang_counts": {"en": 0, "hi": 0, "bn": 0, "ta": 0},
                "top_terms": [],
            },
        }
    finally:
        if close_client and client:
            client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run clustering over embeddings.")
    parser.add_argument("--vectors", default="data/vectors.npy", help="Path to vectors npy")
    parser.add_argument("--db", default=None, help="Database name")
    parser.add_argument("--min-cluster-size", type=int, default=15, help="HDBSCAN min cluster size")
    args = parser.parse_args()

    run_clustering(embeddings_npy=args.vectors, db_name=args.db, min_cluster_size=args.min_cluster_size)
