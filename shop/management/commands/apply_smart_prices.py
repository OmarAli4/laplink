import csv
import json
import os
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from shop.models import Product
from shop.search.indexer import _safe_invalidate_cache


class Command(BaseCommand):
    help = 'Safely applies smart pricing updates and hides duplicate listings (Idempotent & Rollback-Ready).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rollback',
            action='store_true',
            help='Restore all products back to their old_price before smart pricing.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force apply new_price even if current DB price was modified manually.',
        )

    def handle(self, *args, **options):
        rollback = options.get('rollback', False)
        force = options.get('force', False)

        fixture_file = os.path.join(settings.BASE_DIR, 'shop', 'fixtures', 'smart_prices_dataset.json')
        if not os.path.exists(fixture_file):
            self.stdout.write(self.style.ERROR(f"Smart prices fixture not found at: {fixture_file}"))
            return

        with open(fixture_file, 'r', encoding='utf-8') as f:
            dataset = json.load(f)

        # 1. حفظ نسخة احتياطية حية من قاعدة بيانات السيرفر على وحدة التخزين الدائمة (media/backups) لمرة واحدة
        backup_dir = os.path.join(getattr(settings, 'MEDIA_ROOT', settings.BASE_DIR), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        server_backup_csv = os.path.join(backup_dir, 'db_prices_snapshot_before_smart_pricing.csv')

        if not os.path.exists(server_backup_csv):
            try:
                with open(server_backup_csv, 'w', encoding='utf-8-sig', newline='') as bf:
                    writer = csv.writer(bf)
                    writer.writerow(['id', 'slug', 'name', 'price', 'sale_price', 'available', 'stock_quantity'])
                    for prod in Product.objects.all().order_by('id'):
                        writer.writerow([
                            prod.id,
                            prod.slug,
                            prod.name,
                            str(prod.price),
                            str(prod.sale_price or ''),
                            prod.available,
                            prod.stock_quantity,
                        ])
                self.stdout.write(self.style.SUCCESS(f"Created server DB price snapshot at: {server_backup_csv}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not write server backup file: {e}"))

        # 2. تعطيل فهرسة الذكاء الاصطناعي التلقائية أثناء التحديث الجماعي لمنع استهلاك الرام
        old_signal_setting = getattr(settings, 'SEARCH_AUTO_INDEX_ON_SAVE', True)
        settings.SEARCH_AUTO_INDEX_ON_SAVE = False

        updated_count = 0
        hidden_count = 0
        skipped_count = 0

        try:
            products_by_id = {p.id: p for p in Product.objects.all()}

            with transaction.atomic():
                for entry in dataset:
                    pid = int(entry['id'])
                    prod = products_by_id.get(pid)
                    if not prod:
                        continue

                    old_price = Decimal(str(entry['old_price'])).quantize(Decimal('0.01'))
                    new_price = Decimal(str(entry['new_price'])).quantize(Decimal('0.01'))
                    hide_dup = bool(entry.get('hide_duplicate', False))

                    target_price = old_price if rollback else new_price
                    current_effective = Decimal(str(prod.current_price)).quantize(Decimal('0.01'))
                    current_base = Decimal(str(prod.price)).quantize(Decimal('0.01'))

                    # معالجة المنتج المكرر (ID: 292)
                    if hide_dup:
                        if rollback and not prod.available:
                            Product.objects.filter(pk=pid).update(available=True, price=old_price, sale_price=None)
                            updated_count += 1
                        elif not rollback and prod.available:
                            Product.objects.filter(pk=pid).update(available=False, price=new_price, sale_price=None)
                            hidden_count += 1
                            self.stdout.write(f"  [HIDE DUPLICATE #{pid}] '{prod.name}' -> available=False")
                        continue

                    # لا نحدّث السعر إلا إذا كان السعر الحالي يختلف عن السعر المستهدف (أو يساوي السعر القديم/--force/--rollback)
                    should_update = (
                        force
                        or (rollback and (current_base == new_price or current_effective == new_price))
                        or (not rollback and (current_base != target_price or current_base == old_price or current_effective == old_price))
                    )

                    if should_update and (current_base != target_price or prod.sale_price is not None):
                        Product.objects.filter(pk=pid).update(
                            price=target_price,
                            sale_price=None,
                            sale_start=None,
                            sale_end=None,
                        )
                        updated_count += 1
                        self.stdout.write(f"  [#{pid}] '{prod.name[:40]}': {current_effective} -> {target_price} EGP")
                    else:
                        skipped_count += 1

            _safe_invalidate_cache()
        finally:
            settings.SEARCH_AUTO_INDEX_ON_SAVE = old_signal_setting

        mode_label = "ROLLED BACK" if rollback else "UPDATED"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSmart Pricing [{mode_label}]: {updated_count} prices changed, {hidden_count} duplicates hidden, {skipped_count} unchanged/skipped."
            )
        )
