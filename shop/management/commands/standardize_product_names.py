import time
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from shop.models import Product
from shop.ai_service import batch_standardize_product_titles

class Command(BaseCommand):
    help = 'Standardize product titles into clean luxury English e-commerce format using Gemini Flash.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview new titles without updating database')
        parser.add_argument('--batch-size', type=int, default=15, help='Batch size per Gemini API call')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of products to process (0 = all)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        limit = options['limit']

        self.stdout.write("Starting AI Product Title Standardization...")
        if dry_run:
            self.stdout.write("[DRY RUN MODE] No changes will be saved to database.\n")

        products_qs = Product.objects.select_related('category', 'brand').prefetch_related('specs').all().order_by('id')
        if limit > 0:
            products_qs = products_qs[:limit]

        total_prods = products_qs.count()
        self.stdout.write(f"Found {total_prods} products to process.\n")

        prods_list = list(products_qs)
        updated_count = 0

        for i in range(0, total_prods, batch_size):
            batch = prods_list[i:i + batch_size]
            batch_payload = []
            for p in batch:
                specs_dict = {s.name: s.value for s in p.specs.all()[:5]}
                batch_payload.append({
                    'id': p.id,
                    'name': p.name,
                    'category': p.category.name if p.category else '',
                    'brand': p.brand.name if p.brand else '',
                    'description': p.description[:200] if p.description else '',
                    'specs': specs_dict
                })

            self.stdout.write(f"Processing batch {i + 1} to {min(i + batch_size, total_prods)} of {total_prods}...")
            title_map = batch_standardize_product_titles(batch_payload)

            if not title_map:
                self.stdout.write("  [Warning] Batch returned no titles (rate limit or API error). Skipping batch.")
                continue

            for p in batch:
                new_title = title_map.get(p.id)
                if not new_title or new_title == p.name:
                    continue

                old_name = p.name
                if not dry_run:
                    p.name = new_title
                    # Generate clean slug
                    new_slug = slugify(new_title)
                    if new_slug:
                        p.slug = new_slug[:190]
                    p.save(update_fields=['name', 'slug'])

                updated_count += 1
                self.stdout.write(f"  [{p.id}] Old: {old_name}")
                self.stdout.write(f"       New: {new_title}\n")

            # Be nice to free tier RPM quota
            time.sleep(1.5)

        self.stdout.write(f"\nCompleted! Total products updated: {updated_count}/{total_prods}")