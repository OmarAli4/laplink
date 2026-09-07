import json
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.conf import settings
from shop.models import Product

class Command(BaseCommand):
    help = 'Applies the curated standardized product titles mapping to the database safely.'

    def handle(self, *args, **options):
        self.stdout.write("Starting standardized product titles update...")

        dataset_file = os.path.join(settings.BASE_DIR, 'shop', 'fixtures', 'standardized_titles_dataset.json')
        if not os.path.exists(dataset_file):
            self.stdout.write(self.style.ERROR(f"Dataset file not found at: {dataset_file}"))
            return

        with open(dataset_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        self.stdout.write(f"Loaded {len(dataset)} verified title entries from dataset.")

        by_id = {item['id']: item for item in dataset}
        by_slug = {item['old_slug']: item for item in dataset}
        by_name = {item['old_name'].lower().strip(): item for item in dataset}

        updated_count = 0
        products = Product.objects.all()

        for product in products:
            matched_item = None

            # 1. Match by ID with validation
            if product.id in by_id:
                candidate = by_id[product.id]
                # Validate that the product matches slug or name to prevent ID mismatch
                if candidate['old_slug'] in product.slug or product.slug in candidate['old_slug'] or candidate['old_name'].lower() in product.name.lower():
                    matched_item = candidate

            # 2. Match by exact old slug
            if not matched_item and product.slug in by_slug:
                matched_item = by_slug[product.slug]

            # 3. Match by exact old name
            if not matched_item and product.name.lower().strip() in by_name:
                matched_item = by_name[product.name.lower().strip()]

            if matched_item:
                new_title = matched_item['new_name']
                if new_title and new_title != product.name:
                    old_name = product.name
                    product.name = new_title
                    new_slug = slugify(new_title)
                    if new_slug:
                        product.slug = new_slug[:190]
                    product.save(update_fields=['name', 'slug'])
                    updated_count += 1
                    self.stdout.write(f"  [#{product.id}] '{old_name}' -> '{new_title}'")

        self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated_count} products with clean standardized titles!"))