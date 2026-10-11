"""
Signal handlers to auto-index products upon modifications.
Uses transaction.on_commit and daemon threads to ensure asynchronous background processing.
"""
import logging
import threading
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings

from shop.models import Product, ProductSpec, Brand, Category, SubCategory
from .indexer import index_products, _safe_invalidate_cache

logger = logging.getLogger('shop.search')


def _index_in_background(product_ids):
    try:
        from shop.models import Product
        qs = Product.objects.filter(pk__in=product_ids)
        index_products(qs, force=False, use_ai=True)
    except Exception as e:
        logger.error("Background search indexing failed for IDs %s: %s", product_ids, e)


@receiver(post_save, sender=Product)
def product_post_save_handler(sender, instance, created, **kwargs):
    _safe_invalidate_cache()
    if not getattr(settings, 'SEARCH_AUTO_INDEX_ON_SAVE', True):
        return

    pid = instance.id
    transaction.on_commit(
        lambda: threading.Thread(target=_index_in_background, args=([pid],), daemon=True).start()
    )


@receiver(post_save, sender=ProductSpec)
@receiver(post_delete, sender=ProductSpec)
def spec_change_handler(sender, instance, **kwargs):
    _safe_invalidate_cache()
    if not getattr(settings, 'SEARCH_AUTO_INDEX_ON_SAVE', True):
        return

    pid = instance.product_id
    if pid:
        transaction.on_commit(
            lambda: threading.Thread(target=_index_in_background, args=([pid],), daemon=True).start()
        )


@receiver(post_save, sender=Brand)
@receiver(post_delete, sender=Brand)
@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
@receiver(post_save, sender=SubCategory)
@receiver(post_delete, sender=SubCategory)
def relation_change_handler(sender, instance, **kwargs):
    _safe_invalidate_cache()
    if not getattr(settings, 'SEARCH_AUTO_INDEX_ON_SAVE', True):
        return

    try:
        pids = list(instance.products.values_list('id', flat=True))
        if pids:
            transaction.on_commit(
                lambda: threading.Thread(target=_index_in_background, args=(pids,), daemon=True).start()
            )
    except Exception as e:
        logger.warning("Could not resolve affected products for %s: %s", sender, e)
