import sys
from django.core.management.base import BaseCommand
from shop.models import Product
from shop.search.indexer import index_products

# Configure console encoding for Windows cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class Command(BaseCommand):
    help = "Reindex products for LapLink smart search (AI tags, embeddings, and text index)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-generating tags and embeddings even if content hash has not changed',
        )
        parser.add_argument(
            '--no-ai',
            action='store_true',
            help='Rebuild search_text only without invoking Gemini API',
        )
        parser.add_argument(
            '--ids',
            type=str,
            default='',
            help='Comma-separated list of product IDs to index (e.g. --ids 1,2,3)',
        )

    def handle(self, *args, **options):
        force = options['force']
        use_ai = not options['no_ai']
        ids_raw = options['ids'].strip()

        qs = Product.objects.all()
        if ids_raw:
            id_list = [int(i.strip()) for i in ids_raw.split(',') if i.strip().isdigit()]
            qs = qs.filter(id__in=id_list)

        count = qs.count()
        self.stdout.write(f"Starting search re-indexing for {count} products (force={force}, use_ai={use_ai})...")

        stats = index_products(qs, force=force, use_ai=use_ai)

        self.stdout.write(self.style.SUCCESS(
            f"Done! Stats: Total: {stats['total']}, Skipped: {stats['skipped']}, "
            f"Tagged: {stats['tagged']}, Embedded: {stats['embedded']}, Failed: {stats['failed']}"
        ))
