"""
Gemini API client for Smart Search: document embeddings, query embeddings, and tag generation.
Fails softly (returns None) on all API errors or missing credentials.
Uses standard library urllib (no new SDK dependencies).
"""
import os
import json
import time
import math
import hashlib
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from django.conf import settings
from django.core.cache import cache

from .normalize import normalize

logger = logging.getLogger('shop.search')

# Ensure environment is loaded
load_dotenv(override=True)


def _get_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "").strip()


def l2_normalize(vec: List[float]) -> List[float]:
    """L2-normalizes vector and rounds coordinates to 6 decimals."""
    sq_sum = sum(x * x for x in vec)
    if sq_sum <= 0:
        return vec
    norm = math.sqrt(sq_sum)
    return [round(x / norm, 6) for x in vec]


def embed_documents(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Computes document embeddings in batches of <= 100 texts.
    Returns list of normalized embedding vectors, or None on failure.
    """
    if not texts:
        return []

    api_key = _get_api_key()
    if not api_key:
        logger.warning("Gemini API key not configured. Skipping embed_documents.")
        return None

    model = getattr(settings, 'SEARCH_EMBED_MODEL', 'gemini-embedding-001')
    dim = getattr(settings, 'SEARCH_EMBED_DIM', 768)
    batch_size = 100
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk = texts[i:i + batch_size]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={api_key}"
        payload = {
            "requests": [
                {
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": t}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                    "outputDimensionality": dim,
                }
                for t in chunk
            ]
        }

        # Try batch with 1 retry on 429/5xx
        data = None
        for attempt in range(2):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'x-goog-api-key': api_key
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    break
            except urllib.error.HTTPError as e:
                err_body = ""
                try:
                    err_body = e.read().decode('utf-8')
                except Exception:
                    pass
                logger.warning("Gemini batchEmbedContents HTTP error: %s (attempt %s): %s", e.code, attempt + 1, err_body[:200])
                if e.code in (429, 500, 503) and attempt == 0:
                    time.sleep(2)
                    continue
                return None
            except Exception as e:
                logger.error("Gemini batchEmbedContents request error: %s", type(e).__name__)
                if attempt == 0:
                    time.sleep(2)
                    continue
                return None

        if not data or 'embeddings' not in data:
            logger.error("Gemini batchEmbedContents missing embeddings in response.")
            return None

        for item in data['embeddings']:
            vals = item.get('values', [])
            all_embeddings.append(l2_normalize(vals))

    return all_embeddings


def embed_query(text: str) -> Optional[List[float]]:
    """
    Computes query embedding with 2.5s timeout and 7-day caching.
    Returns normalized vector or None on failure.
    """
    if not text or not text.strip():
        return None

    norm_text = normalize(text)
    if not norm_text:
        return None

    # Check cache
    q_hash = hashlib.sha256(norm_text.encode('utf-8')).hexdigest()
    cache_key = f"search:qemb:v1:{q_hash}"
    cached_vec = cache.get(cache_key)
    if cached_vec is not None:
        return cached_vec

    api_key = _get_api_key()
    if not api_key:
        return None

    model = getattr(settings, 'SEARCH_EMBED_MODEL', 'gemini-embedding-001')
    dim = getattr(settings, 'SEARCH_EMBED_DIM', 768)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": norm_text}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": dim,
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'x-goog-api-key': api_key
            }
        )
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            vals = data.get('embedding', {}).get('values', [])
            if not vals:
                return None
            norm_vec = l2_normalize(vals)
            # Cache for 7 days (604800 seconds)
            cache.set(cache_key, norm_vec, timeout=604800)
            return norm_vec
    except Exception as e:
        logger.warning("embed_query soft-fail for query '%s': %s", text[:30], type(e).__name__)
        return None


def generate_tags(products: List[Dict[str, Any]]) -> Optional[Dict[int, Dict[str, Any]]]:
    """
    Generates AI search keywords (English + Arabic) for up to 10 products.
    Returns {product_id: {"product_type": str, "tags_en": list, "tags_ar": list}} or None.
    """
    if not products:
        return {}

    api_key = _get_api_key()
    if not api_key:
        logger.warning("Gemini API key not configured. Skipping generate_tags.")
        return None

    models_to_try = getattr(settings, 'SEARCH_TAG_MODELS', ['gemini-flash-lite-latest', 'gemini-flash-latest'])

    prompt = (
        "You generate e-commerce search keywords for an Egyptian electronics store. "
        "For each product, output what a shopper might type to find it: the generic product type, "
        "common alternative names, use cases, and Egyptian Arabic terms and transliterations "
        "(e.g. how Egyptians write brand/product names in Arabic letters). Do not invent specs. "
        "Do not include other brands. Max 12 English and 12 Arabic keywords per product, lowercase, no duplicates. "
        'Return JSON: {"items":[{"id":<int>,"product_type":"<short english>","tags_en":[...],"tags_ar":[...]}]}.\n'
        f"Products: {json.dumps(products, ensure_ascii=False)}"
    )

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 8000
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()

                if '```json' in raw_text:
                    raw_text = raw_text.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_text:
                    raw_text = raw_text.split('```')[1].split('```')[0].strip()

                parsed = json.loads(raw_text)
                items = parsed.get('items', [])
                out = {}
                for it in items:
                    pid = it.get('id')
                    if pid is not None:
                        out[int(pid)] = {
                            "product_type": str(it.get('product_type', '')),
                            "tags_en": [str(t).lower().strip() for t in it.get('tags_en', []) if str(t).strip()],
                            "tags_ar": [str(t).strip() for t in it.get('tags_ar', []) if str(t).strip()],
                        }
                return out
        except urllib.error.HTTPError as e:
            err_body = ""
            try:
                err_body = e.read().decode('utf-8')
            except Exception:
                pass
            logger.warning("Gemini generate_tags HTTP error %s on model %s: %s", e.code, model_name, err_body[:300])
            if e.code in (429, 500, 503):
                time.sleep(3)
            continue
        except Exception as e:
            logger.warning("Gemini generate_tags error on model %s: %s", model_name, e)
            continue

    return None
