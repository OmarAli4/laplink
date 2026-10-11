"""
Indexing engine for LapLink Smart Search.
Builds searchable documents, content hashes, and integrates with Gemini embedding/tagging.
Uses Product.objects.filter().update() to prevent cascading signals or redundant image processing.
"""
import time
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db.models import QuerySet

from .normalize import normalize
from . import gemini

logger = logging.getLogger('shop.search')


def build_source(product) -> Dict[str, Any]:
    """
    Extracts raw structured content for hashing and indexing.
    Expected relations: brand, category, subcategory, specs.
    """
    specs_list = []
    if hasattr(product, 'specs'):
        for s in product.specs.all():
            specs_list.append(f"{s.name}: {s.value}")

    return {
        "id": product.id,
        "name": product.name or "",
        "brand": product.brand.name if product.brand else "",
        "category": product.category.name if product.category else "",
        "subcategory": product.subcategory.name if product.subcategory else "",
        "subcategory_ar": getattr(product.subcategory, 'name_ar', '') if product.subcategory else "",
        "specs": specs_list,
        "description": (product.description or "")[:1000],
    }


def content_hash(source: Dict[str, Any]) -> str:
    """Computes SHA-256 of source dict (excluding tags/embeddings)."""
    serialized = json.dumps(source, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def build_search_text(source: Dict[str, Any], search_tags: str = "") -> str:
    """
    Builds a weighted-field document string with field prefixes:
    N|<name>
    B|<brand>
    C|<category> <subcategory> <subcategory_ar>
    T|<search_tags>
    S|<specs>
    D|<description>
    """
    n_val = normalize(source.get("name", ""))
    b_val = normalize(source.get("brand", ""))
    c_parts = [source.get("category", ""), source.get("subcategory", ""), source.get("subcategory_ar", "")]
    c_val = normalize(" ".join(p for p in c_parts if p))
    t_val = normalize(search_tags or "")
    s_val = normalize(" ; ".join(source.get("specs", [])))
    d_val = normalize(source.get("description", ""))

    lines = [
        f"N|{n_val}",
        f"B|{b_val}",
        f"C|{c_val}",
        f"T|{t_val}",
        f"S|{s_val}",
        f"D|{d_val}",
    ]
    return "\n".join(lines)


def build_embedding_document(source: Dict[str, Any], tag_info: Optional[Dict[str, Any]] = None) -> str:
    """
    Builds a rich, natural language document for Gemini embedding (un-normalized).
    """
    name = source.get("name", "")
    brand = source.get("brand", "")
    cat = source.get("category", "")
    sub = source.get("subcategory", "")
    specs_str = ", ".join(source.get("specs", []))
    desc = source.get("description", "")[:500]

    product_type = ""
    keywords_list = []
    if tag_info:
        product_type = tag_info.get("product_type", "")
        keywords_list = tag_info.get("tags_en", []) + tag_info.get("tags_ar", [])
    keywords_str = ", ".join(keywords_list)

    doc_parts = [f"{name}."]
    if brand:
        doc_parts.append(f"Brand: {brand}.")
    if cat or sub:
        doc_parts.append(f"Category: {cat} > {sub}." if sub else f"Category: {cat}.")
    if product_type:
        doc_parts.append(f"Type: {product_type}.")
    if keywords_str:
        doc_parts.append(f"Keywords: {keywords_str}.")
    if specs_str:
        doc_parts.append(f"Specs: {specs_str}.")
    if desc:
        doc_parts.append(desc)

    return " ".join(doc_parts)


def index_products(queryset: QuerySet, force: bool = False, use_ai: bool = True) -> Dict[str, int]:
    """
    Indexes the given queryset of products.
    Updates search_text, search_tags, search_embedding, and search_hash via .update().
    """
    from shop.models import Product

    products = list(queryset.select_related('brand', 'category', 'subcategory').prefetch_related('specs'))
    stats = {
        "total": len(products),
        "skipped": 0,
        "tagged": 0,
        "embedded": 0,
        "failed": 0,
    }

    if not products:
        return stats

    stale_items = []

    for p in products:
        src = build_source(p)
        h = content_hash(src)

        if not force and p.search_hash == h and p.search_embedding:
            # Hash matches and embedding exists: just refresh search_text in case tags or format changed
            new_text = build_search_text(src, p.search_tags or "")
            if p.search_text != new_text:
                Product.objects.filter(pk=p.pk).update(search_text=new_text)
            stats["skipped"] += 1
        else:
            stale_items.append((p, src, h))

    if not stale_items:
        _safe_invalidate_cache()
        return stats

    # If use_ai is disabled or no API key, update search_text only
    api_key = gemini._get_api_key()
    if not use_ai or not api_key:
        now = timezone.now()
        for p, src, h in stale_items:
            new_text = build_search_text(src, p.search_tags or "")
            Product.objects.filter(pk=p.pk).update(
                search_text=new_text,
                search_indexed_at=now
            )
        _safe_invalidate_cache()
        return stats

    # Process AI tagging in chunks of 5
    tag_results: Dict[int, Dict[str, Any]] = {}
    chunk_size = 5
    for i in range(0, len(stale_items), chunk_size):
        chunk = stale_items[i:i + chunk_size]
        payload = []
        for p, src, _ in chunk:
            specs_dict = {}
            for s in src.get("specs", []):
                if ":" in s:
                    k, v = s.split(":", 1)
                    specs_dict[k.strip()] = v.strip()
            payload.append({
                "id": p.id,
                "name": src.get("name", ""),
                "brand": src.get("brand", ""),
                "category": src.get("category", ""),
                "subcategory": src.get("subcategory", ""),
                "specs": specs_dict,
                "description": src.get("description", "")[:400],
            })
        
        if i > 0:
            time.sleep(1.0)
        tags_data = gemini.generate_tags(payload)
        if tags_data:
            tag_results.update(tags_data)
            stats["tagged"] += len(tags_data)

    # Prepare embedding documents
    doc_texts = []
    for p, src, _ in stale_items:
        t_info = tag_results.get(p.id)
        doc_texts.append(build_embedding_document(src, t_info))

    embeddings = gemini.embed_documents(doc_texts)
    if embeddings and len(embeddings) == len(stale_items):
        stats["embedded"] += len(embeddings)
    else:
        logger.warning("Embedding generation returned None or mismatched count.")
        stats["failed"] += len(stale_items)
        embeddings = [None] * len(stale_items)

    now = timezone.now()
    for idx, (p, src, h) in enumerate(stale_items):
        emb = embeddings[idx]
        t_info = tag_results.get(p.id)

        # Retain staff-edited search_tags if already set and not force
        if p.search_tags and not force and p.search_hash:
            tags_to_store = p.search_tags
        elif t_info:
            all_tags = t_info.get("tags_en", []) + t_info.get("tags_ar", [])
            tags_to_store = ", ".join(all_tags)
        else:
            tags_to_store = p.search_tags or ""

        search_txt = build_search_text(src, tags_to_store)

        update_kwargs = {
            "search_text": search_txt,
            "search_tags": tags_to_store,
            "search_indexed_at": now,
        }

        if emb is not None:
            update_kwargs["search_embedding"] = emb
            update_kwargs["search_hash"] = h
        # If AI failed to embed, do not update search_hash so it retries on subsequent runs

        Product.objects.filter(pk=p.pk).update(**update_kwargs)

    _safe_invalidate_cache()
    return stats


def _safe_invalidate_cache():
    try:
        from .engine import invalidate_cache
        invalidate_cache()
    except ImportError:
        pass
