"""Provider clients used by optional credibility helpers."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional
import google.generativeai as genai
import openai
from openai import AsyncOpenAI, OpenAI

from core.config import get_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def get_openai_client() -> Optional[OpenAI]:
    """Initialize and return OpenAI client if OPENAI_API_KEY is present."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key in ("your_openai_api_key_here", "your_key_here"):
        return None
    try:
        return OpenAI(api_key=api_key, max_retries=0, timeout=45)
    except Exception as e:
        logger.error("Failed to initialize OpenAI client: %s", e)
        return None


def get_async_openai_client() -> Optional[AsyncOpenAI]:
    """Build the bounded asynchronous client used by Ask's wall-clock deadline."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key in ("your_openai_api_key_here", "your_key_here"):
        return None
    try:
        return AsyncOpenAI(api_key=api_key, max_retries=0, timeout=45)
    except Exception as e:
        logger.error("Failed to initialize OpenAI async client: %s", e)
        return None


def get_gemini_client() -> Optional[Any]:
    """Initialize and return Gemini generative model client if API key is present."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key in ("your_gemini_api_key_here", "your_key_here"):
        return None

    try:
        cfg = get_config()
        model_name = cfg.get("gemini", {}).get("model", "gemini-1.5-flash")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name)
        return model
    except Exception as e:
        logger.error("Failed to initialize Gemini client: %s", e)
        return None


def get_llm_client() -> Optional[Any]:
    """Return primary LLM client (OpenAI first, fallback to Gemini)."""
    openai_client = get_openai_client()
    if openai_client is not None:
        return openai_client
    return get_gemini_client()
