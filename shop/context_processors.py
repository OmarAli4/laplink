from django.db.models import Prefetch
from .models import Category, Brand, Announcement

def category_navbar(request):
    """
    Global context processor to pre-fetch categories and brands
    for the luxury Alpine.js dropdown menus.
    """
    categories = Category.objects.prefetch_related('brands').all()
    brands = Brand.objects.all()
    announcements = Announcement.objects.filter(is_active=True).order_by('order')
    
    return {
        'navbar_categories': categories,
        'navbar_brands': brands,
        'active_announcements': announcements,
    }
