"""
LapLink Smart Search Package
"""
from .engine import search, invalidate_cache, SearchResult
from .indexer import index_products

__all__ = [
    'search',
    'index_products',
    'invalidate_cache',
    'SearchResult',
]
