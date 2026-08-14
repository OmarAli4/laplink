from django.core.management.base import BaseCommand
from shop.models import Product, Category

class Command(BaseCommand):
    help = 'Safely deletes dummy seed products without touching user products or uploaded images'

    def handle(self, *args, **options):
        dummy_slugs = [
            'iphone-16-pro-max', 'samsung-galaxy-s25-ultra', 'google-pixel-9-pro',
            'macbook-pro-16-m4-max', 'dell-xps-15', 'lenovo-thinkpad-x1-carbon',
            'sony-wh-1000xm6', 'airpods-pro-3', 'bose-quietcomfort-ultra',
            'sony-alpha-a7-iv', 'canon-eos-r6-mark-ii', 'playstation-5-pro',
            'nintendo-switch-2', 'xbox-series-x', 'apple-watch-ultra-3',
            'samsung-t9-portable-ssd-2tb', 'anker-737-power-bank-24k'
        ]
        
        # Safely delete ONLY dummy products that have no image attached
        deleted_count, _ = Product.objects.filter(slug__in=dummy_slugs, image='').delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} dummy products."))

        # Clean up empty categories that have zero products
        for category in Category.objects.all():
            if category.products.count() == 0:
                category.delete()
                self.stdout.write(f"Removed empty category: {category.name}")
