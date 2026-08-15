from django.core.management.base import BaseCommand
from shop.models import Product
from shop.ai_service import analyze_product_images_with_vision
import time

class Command(BaseCommand):
    help = 'Automatically inspects all product cover and gallery photos with Google Gemini Vision and populates Color, Type, and Material specs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-analyze even if products already have Color specs',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        products = Product.objects.filter(available=True)
        
        self.stdout.write(self.style.SUCCESS(f"🚀 Found {products.count()} active products to check with Gemini Vision..."))
        
        tagged_count = 0
        for p in products:
            has_color = p.specs.filter(name__iexact='color').exists()
            if has_color and not force:
                self.stdout.write(f" - Skipping '{p.name}' (already has Color spec: {p.specs.filter(name__iexact='color').first().value})")
                continue
                
            self.stdout.write(f" 🔍 Analyzing visual photos for '{p.name}'...")
            res = analyze_product_images_with_vision(p.id)
            if res.get('success'):
                data = res.get('data', {})
                color = data.get('primary_color', 'N/A')
                item_type = data.get('item_type', 'N/A')
                self.stdout.write(self.style.SUCCESS(f"   ✔ Success! Color: {color} | Type: {item_type}"))
                tagged_count += 1
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠ Could not analyze: {res.get('error')}"))
                
            time.sleep(0.5) # gentle pacing for API limits
            
        self.stdout.write(self.style.SUCCESS(f"🎉 Done! Successfully auto-tagged {tagged_count} products with AI Vision specs."))
