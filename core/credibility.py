"""Credibility and veracity assessment module for Multilingual News Intelligence Platform.

Classifies article veracity (Likely reliable, Uncertain, Likely misleading),
evaluates cross-source agreement via LLM entailment (OpenAI / Gemini) or heuristic analysis,
and augments citation metadata.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from core.config import get_config
from core.rag import get_llm_client, get_gemini_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

VALID_VERACITIES = ["Likely reliable", "Uncertain", "Likely misleading"]


def label_article(
    article_text: str,
    article_title: str,
    llm_client: Optional[Any] = None,
    gemini_client: Optional[Any] = None,
) -> Dict[str, str]:
    """Classify article veracity as Likely reliable, Uncertain, or Likely misleading with reason.

    Args:
        article_text: Content or snippet of the article.
        article_title: Title/headline of the article.
        llm_client: Optional OpenAI or Gemini client.
        gemini_client: Alias for backward compatibility.

    Returns:
        Dict with keys: 'veracity' and 'reason'.
    """
    client = llm_client or gemini_client or get_llm_client()

    if client is not None:
        prompt = (
            "You are a factual verification assistant. Evaluate the following news passage.\n"
            f"Title: {article_title}\n"
            f"Passage: {article_text[:600]}\n\n"
            "Respond in JSON format with exactly two keys:\n"
            '- "veracity": one of ["Likely reliable", "Uncertain", "Likely misleading"]\n'
            '- "reason": one clear sentence explaining why.\n\n'
            "JSON:"
        )
        try:
            raw = ""
            # OpenAI
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                model_name = get_config().get("openai", {}).get("model", "gpt-6-luna")
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256,
                )
                raw = resp.choices[0].message.content.strip() if resp.choices else ""
            # Gemini
            elif hasattr(client, "generate_content"):
                resp = client.generate_content(prompt)
                raw = resp.text.strip() if hasattr(resp, "text") and resp.text else ""

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                veracity = data.get("veracity", "").strip()
                reason = data.get("reason", "").strip()
                if veracity in VALID_VERACITIES and reason:
                    return {"veracity": veracity, "reason": reason}
        except Exception as e:
            logger.warning("LLM credibility labeling failed (%s). Using fallback.", e)

    # Heuristic fallback for offline/demo operation
    lowered = f"{article_title} {article_text}".lower()
    misleading_keywords = ["shocking truth", "miracle cure", "illuminati", "hoax", "conspiracy", "secret plot"]
    uncertain_keywords = ["unconfirmed", "allegedly", "rumors suggest", "sources say maybe", "speculation"]

    if any(k in lowered for k in misleading_keywords):
        return {
            "veracity": "Likely misleading",
            "reason": "Contains sensationalist or unverified speculative phrasing.",
        }
    elif any(k in lowered for k in uncertain_keywords):
        return {
            "veracity": "Uncertain",
            "reason": "Claims are based on anonymous or unconfirmed preliminary reports.",
        }
    else:
        return {
            "veracity": "Likely reliable",
            "reason": "Article aligns with corroborated journalistic reporting standards.",
        }


def compute_agreement(
    query: str,
    chunks: List[Dict[str, Any]],
    cited_chunks: Optional[List[Dict[str, Any]]] = None,
    llm_client: Optional[Any] = None,
    gemini_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute cross-source agreement score and summary label.

    Args:
        query: User query or claim to verify.
        chunks: All retrieved candidate chunks.
        cited_chunks: Chunks actually cited in the generated answer.
        llm_client: Optional OpenAI or Gemini client.
        gemini_client: Alias for backward compatibility.

    Returns:
        Dict matching CredibilityResult: {"agreement_score": float, "agreement_label": str}.
    """
    if not cited_chunks and not chunks:
        return {
            "agreement_score": 0.0,
            "agreement_label": "No corroborating sources found.",
        }

    eval_set = cited_chunks if cited_chunks else chunks[:3]
    client = llm_client or gemini_client or get_llm_client()

    if client is not None and len(eval_set) > 1:
        passages_text = "\n".join(
            f"Source {i+1} ({c.get('lang', 'en')}): {c.get('text', '')[:300]}"
            for i, c in enumerate(eval_set)
        )
        prompt = (
            f"Question / Claim: {query}\n\n"
            f"Sources:\n{passages_text}\n\n"
            "Evaluate whether these sources agree with each other on the core facts.\n"
            "Return JSON with two keys:\n"
            '- "agreement_score": a float between 0.0 and 1.0 representing proportion of sources that agree\n'
            '- "agreement_label": a brief string describing the consensus (e.g. "High cross-source agreement", "Partial agreement with conflicting claims", "Inconclusive")\n\n'
            "JSON:"
        )
        try:
            raw = ""
            if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                model_name = get_config().get("openai", {}).get("model", "gpt-6-luna")
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256,
                )
                raw = resp.choices[0].message.content.strip() if resp.choices else ""
            elif hasattr(client, "generate_content"):
                resp = client.generate_content(prompt)
                raw = resp.text.strip() if hasattr(resp, "text") and resp.text else ""

            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                score = float(data.get("agreement_score", 0.85))
                score = max(0.0, min(1.0, score))
                label = str(data.get("agreement_label", "Moderate agreement across sources"))
                return {"agreement_score": round(score, 2), "agreement_label": label}
        except Exception as e:
            logger.warning("LLM agreement scoring failed (%s). Using fallback calculation.", e)

    # Deterministic fallback agreement computation
    n = len(eval_set)
    if n == 0:
        return {"agreement_score": 0.0, "agreement_label": "Insufficient sources"}
    elif n == 1:
        return {"agreement_score": 0.70, "agreement_label": "Single source corroboration"}

    # Distinct languages represented
    langs = set(c.get("lang", "en").lower() for c in eval_set)
    # Check veracity of items
    reliable_count = sum(1 for c in eval_set if c.get("veracity", "Likely reliable") == "Likely reliable")
    ratio = reliable_count / n

    if len(langs) > 1 and ratio >= 0.75:
        score = 0.90
        label = f"High multilingual consensus ({len(langs)} languages)"
    elif ratio >= 0.75:
        score = 0.85
        label = "High cross-source agreement"
    elif ratio >= 0.5:
        score = 0.65
        label = "Moderate agreement across sources"
    else:
        score = 0.35
        label = "Conflicting or uncertain accounts"

    return {"agreement_score": round(score, 2), "agreement_label": label}


def label_all_citations(
    citations: List[Dict[str, Any]],
    llm_client: Optional[Any] = None,
    gemini_client: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Augment a list of citation dictionaries with veracity classifications.

    Args:
        citations: List of citation metadata dicts.
        llm_client: Optional OpenAI or Gemini client.
        gemini_client: Alias for backward compatibility.

    Returns:
        List of augmented citation dicts with 'veracity' and 'reason'.
    """
    client = llm_client or gemini_client or get_llm_client()
    augmented: List[Dict[str, Any]] = []

    for cit in citations:
        text = cit.get("snippet", "") or cit.get("text", "")
        title = cit.get("title", "")
        res = label_article(text, title, llm_client=client)

        c_copy = dict(cit)
        c_copy["veracity"] = res["veracity"]
        c_copy["reason"] = res["reason"]
        augmented.append(c_copy)

    return augmented
