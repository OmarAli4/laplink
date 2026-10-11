"""
Semantic vector search ranker for LapLink Smart Search.
Calculates cosine similarity (dot product of L2-normalized vectors) between query and products.
Fails softly when embeddings are unavailable or API calls fail.
"""
import logging
from typing import List, Tuple, Dict, Any
from django.conf import settings

from . import gemini

logger = logging.getLogger('shop.search')


def semantic_rank(query: str, index: Dict[str, Any]) -> List[Tuple[int, float]]:
    """
    Ranks products by vector semantic similarity to the query.
    Returns list of (product_id, similarity) sorted descending, filtered by SEARCH_SEMANTIC_MIN_SIM.
    """
    if not getattr(settings, 'SEARCH_ENABLE_SEMANTIC', True):
        return []

    products = index.get("items", [])
    products_with_embeddings = [p for p in products if p.get("embedding")]
    if not products_with_embeddings:
        return []

    try:
        q_vec = gemini.embed_query(query)
    except Exception as e:
        logger.warning("Error computing query embedding: %s", e)
        return []

    if not q_vec:
        return []

    min_sim = float(getattr(settings, 'SEARCH_SEMANTIC_MIN_SIM', 0.0))
    results = []

    for p in products_with_embeddings:
        p_vec = p["embedding"]
        if not p_vec or len(p_vec) != len(q_vec):
            continue

        # Cosine similarity (dot product of L2-normalized vectors)
        sim = sum(a * b for a, b in zip(q_vec, p_vec))
        if sim >= min_sim:
            results.append((p["id"], round(sim, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:50]
