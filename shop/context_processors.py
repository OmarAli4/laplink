from django.db.models import Prefetch
from .models import Category, Brand, Announcement

def category_navbar(request):
    """
    Global context processor to pre-fetch categories, subcategories, and brands
    for the luxury Alpine.js dropdown menus.
    """
    avail_cats = Category.objects.filter(products__available=True).distinct().prefetch_related('subcategories', 'brands')
    categories = avail_cats if avail_cats.exists() else Category.objects.prefetch_related('subcategories', 'brands').all()
    avail_brands = Brand.objects.filter(products__available=True).distinct()
    brands = avail_brands if avail_brands.exists() else Brand.objects.all()
    announcements = Announcement.objects.filter(is_active=True).order_by('order')
    
    return {
        'navbar_categories': categories,
        'navbar_brands': brands,
        'active_announcements': announcements,
    }
