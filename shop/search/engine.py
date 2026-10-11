"""
Smart Search Engine orchestration for LapLink.
Handles in-memory indexing, Reciprocal Rank Fusion (RRF), category fallback, and caching.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.core.cache import cache

from .normalize import tokenize, stem
from .keyword import keyword_rank
from .semantic import semantic_rank

logger = logging.getLogger('shop.search')

CACHE_KEY_INDEX = "search:index:v1"
CACHE_TIMEOUT = 3600  # 1 hour

_LOCAL_INDEX: Optional[Dict[str, Any]] = None
_LOCAL_VERSION: int = 0


@dataclass
class SearchResult:
    ids: List[int]
    scope_expanded: bool = False
    mode: str = "keyword"  # "hybrid" | "keyword" | "empty"
    debug: Dict[str, Any] = field(default_factory=dict)


def invalidate_cache():
    """Invalidates the in-memory and shared cache index."""
    global _LOCAL_INDEX, _LOCAL_VERSION
    _LOCAL_INDEX = None
    _LOCAL_VERSION += 1
    cache.delete(CACHE_KEY_INDEX)


def _load_index() -> Dict[str, Any]:
    """
    Loads and parses product searchable documents into memory.
    Constructs per-field token sets, stems, and global vocabulary.
    """
    global _LOCAL_INDEX
    if _LOCAL_INDEX is not None:
        return _LOCAL_INDEX

    cached_data = cache.get(CACHE_KEY_INDEX)
    if cached_data is not None:
        _LOCAL_INDEX = cached_data
        return _LOCAL_INDEX

    from shop.models import Product

    products_qs = Product.objects.filter(available=True).values(
        'id', 'category_id', 'subcategory__slug', 'search_text', 'search_embedding'
    )

    items = []
    vocab = set()

    for p in products_qs:
        pid = p['id']
        cat_id = p['category_id']
        sub_slug = p['subcategory__slug']
        s_text = p['search_text'] or ""
        emb = p['search_embedding']

        fields: Dict[str, set] = {'N': set(), 'B': set(), 'C': set(), 'T': set(), 'S': set(), 'D': set()}
        stems: Dict[str, set] = {'N': set(), 'B': set(), 'C': set(), 'T': set(), 'S': set(), 'D': set()}

        if s_text:
            for line in s_text.split('\n'):
                if '|' in line:
                    code, val = line.split('|', 1)
                    if code in fields:
                        t_list = tokenize(val)
                        t_set = set(t_list)
                        fields[code] = t_set
                        stems[code] = {stem(t) for t in t_set}
                        vocab.update(t_set)

        items.append({
            "id": pid,
            "category_id": cat_id,
            "subcategory_slug": sub_slug,
            "fields": fields,
            "stems": stems,
            "embedding": emb,
        })

    index_data = {
        "items": items,
        "vocab": vocab,
    }

    cache.set(CACHE_KEY_INDEX, index_data, timeout=CACHE_TIMEOUT)
    _LOCAL_INDEX = index_data
    return _LOCAL_INDEX


def _filter_index_by_scope(index: Dict[str, Any], category_id: Optional[int], subcategory_slug: Optional[str]) -> Dict[str, Any]:
    """Returns a view of index filtered by category and/or subcategory."""
    items = index.get("items", [])
    filtered_items = []
    for it in items:
        if category_id is not None and it["category_id"] != category_id:
            continue
        if subcategory_slug is not None and it["subcategory_slug"] != subcategory_slug:
            continue
        filtered_items.append(it)

    return {
        "items": filtered_items,
        "vocab": index.get("vocab", set()),
    }


def search(
    query: str,
    category: Any = None,
    subcategory_slug: Optional[str] = None,
    limit: Optional[int] = None
) -> SearchResult:
    """
    Main entry point for smart search.
    Executes keyword and semantic ranking, performs Reciprocal Rank Fusion,
    and falls back to global catalog if category-scoped search returns 0 results.
    """
    if not query or not query.strip():
        return SearchResult(ids=[], mode="empty")

    cleaned_query = query.strip()
    full_index = _load_index()

    # Resolve category ID if category model instance or ID was provided
    cat_id = None
    if category is not None:
        if hasattr(category, 'id'):
            cat_id = category.id
        elif isinstance(category, int):
            cat_id = category
        elif str(category).isdigit():
            cat_id = int(category)

    # 1. Scoped search
    scoped_index = full_index
    is_scoped = (cat_id is not None or subcategory_slug is not None)
    if is_scoped:
        scoped_index = _filter_index_by_scope(full_index, cat_id, subcategory_slug)

    kw_hits = keyword_rank(cleaned_query, scoped_index)
    sem_hits = semantic_rank(cleaned_query, scoped_index)

    k_rrf = getattr(settings, 'SEARCH_RRF_K', 60)
    rrf_scores: Dict[int, float] = {}

    for rank, (pid, _) in enumerate(kw_hits, start=1):
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + (1.0 / (k_rrf + rank))

    for rank, (pid, _) in enumerate(sem_hits, start=1):
        rrf_scores[pid] = rrf_scores.get(pid, 0.0) + (1.0 / (k_rrf + rank))

    ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    ranked_ids = [pid for pid, _ in ranked]
    scope_expanded = False

    # 2. Scope fallback if category search returns 0 results
    if is_scoped and not ranked_ids:
        kw_global = keyword_rank(cleaned_query, full_index)
        sem_global = semantic_rank(cleaned_query, full_index)

        global_rrf: Dict[int, float] = {}
        for rank, (pid, _) in enumerate(kw_global, start=1):
            global_rrf[pid] = global_rrf.get(pid, 0.0) + (1.0 / (k_rrf + rank))
        for rank, (pid, _) in enumerate(sem_global, start=1):
            global_rrf[pid] = global_rrf.get(pid, 0.0) + (1.0 / (k_rrf + rank))

        global_ranked = sorted(global_rrf.items(), key=lambda x: x[1], reverse=True)
        if global_ranked:
            ranked_ids = [pid for pid, _ in global_ranked]
            scope_expanded = True
            kw_hits = kw_global
            sem_hits = sem_global

    mode = "hybrid" if sem_hits else "keyword"

    if limit is not None:
        ranked_ids = ranked_ids[:limit]

    debug_info = {
        "kw_top10": kw_hits[:10],
        "sem_top10": sem_hits[:10],
        "rrf_count": len(ranked_ids),
    }

    return SearchResult(
        ids=ranked_ids,
        scope_expanded=scope_expanded,
        mode=mode,
        debug=debug_info
    )
