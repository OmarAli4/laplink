import sys
import time
from typing import List, Dict, Any, Tuple
from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import Category, SubCategory, Brand, Product, ProductSpec
from shop.search.indexer import index_products
from shop.search.engine import search, invalidate_cache, _load_index
from shop.search import gemini
from shop.search.semantic import semantic_rank
from shop.search.keyword import keyword_rank

# Configure console encoding for Windows cp1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


class Command(BaseCommand):
    help = "Run live evaluation suite against real Gemini API and calibrate similarity threshold"

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("LapLink Smart Search Live Evaluation & Calibration")
        self.stdout.write("==================================================")

        api_key = gemini._get_api_key()
        if not api_key:
            self.stdout.write(self.style.ERROR("ERROR: GEMINI_API_KEY is not set. Cannot run live evaluation."))
            return

        try:
            with transaction.atomic():
                self._run_eval()
                # Force rollback to keep DB clean
                transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Evaluation encountered exception: {e}"))
            raise e

        # Ensure cache is invalidated after rollback
        invalidate_cache()
        self.stdout.write(self.style.SUCCESS("Database rollback completed. db.sqlite3 remains clean."))

    def _run_eval(self):
        self.stdout.write("1. Creating 12 realistic fixture products in rollback transaction...")
        
        # Categories
        cat_audio = Category.objects.create(name="Audio", slug="eval-audio")
        cat_bags = Category.objects.create(name="Bags", slug="eval-bags")
        cat_charging = Category.objects.create(name="Charging", slug="eval-charging")
        cat_laptops = Category.objects.create(name="Laptops", slug="eval-laptops")
        cat_acc = Category.objects.create(name="Computer Accessories", slug="eval-acc")
        cat_network = Category.objects.create(name="Networking", slug="eval-network")

        # Subcategories
        sub_earbuds = SubCategory.objects.create(category=cat_audio, name="Wireless Earbuds", slug="eval-earbuds")
        sub_overear = SubCategory.objects.create(category=cat_audio, name="Over-Ear", slug="eval-overear")
        sub_gaming = SubCategory.objects.create(category=cat_laptops, name="Gaming Laptops", slug="eval-gaming")

        # Brands
        b_apple = Brand.objects.create(name="Apple", slug="eval-apple")
        b_sony = Brand.objects.create(name="Sony", slug="eval-sony")
        b_bange = Brand.objects.create(name="Bange", slug="eval-bange")
        b_anker = Brand.objects.create(name="Anker", slug="eval-anker")
        b_logi = Brand.objects.create(name="Logitech", slug="eval-logi")
        b_lenovo = Brand.objects.create(name="Lenovo", slug="eval-lenovo")
        b_baseus = Brand.objects.create(name="Baseus", slug="eval-baseus")
        b_ugreen = Brand.objects.create(name="Ugreen", slug="eval-ugreen")
        b_tomtoc = Brand.objects.create(name="Tomtoc", slug="eval-tomtoc")
        b_keychron = Brand.objects.create(name="Keychron", slug="eval-keychron")
        b_tplink = Brand.objects.create(name="TP-Link", slug="eval-tplink")
        b_wacom = Brand.objects.create(name="Wacom", slug="eval-wacom")

        products_data = [
            ("Apple AirPods Pro 2 USB-C", "eval-airpods", cat_audio, sub_earbuds, b_apple,
             "Wireless earbuds with active noise cancellation and spatial audio.", 249.00,
             [("Connectivity", "Bluetooth 5.3"), ("Features", "ANC, MagSafe")]),
            ("Sony WH-1000XM5", "eval-sony-xm5", cat_audio, sub_overear, b_sony,
             "Noise cancelling wireless over-ear headset with multipoint.", 399.00,
             [("Battery", "30 hours"), ("Type", "Over-Ear")]),
            ("Bange 1908 Waterproof Travel Laptop Backpack", "eval-bange-1908", cat_bags, None, b_bange,
             "Anti-theft business bag for 15.6 inch laptops with USB charging port.", 45.00,
             [("Water Resistance", "IPX6"), ("Laptop Fit", "15.6 inch")]),
            ("Anker 737 Power Bank 24K", "eval-anker-737", cat_charging, None, b_anker,
             "140W portable charger with smart digital display and 3 output ports.", 149.00,
             [("Capacity", "24000 mAh"), ("Max Output", "140W")]),
            ("Logitech MX Master 3S Mouse", "eval-mx-master", cat_acc, None, b_logi,
             "Ergonomic wireless mouse with quiet clicks and 8K DPI sensor.", 99.00,
             [("DPI", "8000"), ("Connectivity", "Bluetooth, Logi Bolt")]),
            ("Lenovo Legion 5 Gaming Laptop", "eval-legion-5", cat_laptops, sub_gaming, b_lenovo,
             "High performance gaming laptop with Intel i7 and RTX 4060 graphics.", 1299.00,
             [("RAM", "16 GB"), ("GPU", "RTX 4060")]),
            ("Baseus 100W USB-C Fast Charging Cable", "eval-baseus-cable", cat_charging, None, b_baseus,
             "Durable braided USB-C to USB-C charging cord with E-Marker chip.", 15.00,
             [("Length", "2m"), ("Power", "100W Power Delivery")]),
            ("Ugreen Nexode 65W GaN Fast Charger", "eval-ugreen-65w", cat_charging, None, b_ugreen,
             "Compact 3-port GaN wall plug charger for laptops, phones and tablets.", 39.00,
             [("Ports", "2x USB-C, 1x USB-A"), ("Technology", "GaN Fast Charge")]),
            ("Tomtoc 360 Protective Laptop Sleeve 15.6", "eval-tomtoc-sleeve", cat_bags, None, b_tomtoc,
             "CornerArmor shockproof slim notebook case bag for 15.6 laptops.", 32.00,
             [("Protection", "CornerArmor 360"), ("Size", "15.6 inch")]),
            ("Keychron K2 Wireless Mechanical Keyboard", "eval-keychron-k2", cat_acc, None, b_keychron,
             "75% layout compact Bluetooth mechanical keyboard with RGB backlight.", 89.00,
             [("Switches", "Gateron Brown"), ("Layout", "75% 84-Key")]),
            ("TP-Link Archer AX55 Wi-Fi 6 Router", "eval-tplink-ax55", cat_network, None, b_tplink,
             "Dual-band gigabit wireless internet router with OFDMA and OneMesh.", 95.00,
             [("Wi-Fi Standard", "Wi-Fi 6 AX3000"), ("Ethernet", "Gigabit")]),
            ("Wacom Intuos Pro Medium Graphics Tablet", "eval-wacom-intuos", cat_acc, None, b_wacom,
             "Professional digital pen drawing pad for photo editing and artists.", 379.00,
             [("Pressure Levels", "8192"), ("Active Area", "Medium 10x6 in")]),
        ]

        prods_map: Dict[str, Product] = {}
        eval_products: List[Product] = []

        for name, slug, cat, sub, brand, desc, price, specs in products_data:
            p = Product.objects.create(
                name=name,
                slug=slug,
                category=cat,
                subcategory=sub,
                brand=brand,
                description=desc,
                price=price,
                available=True
            )
            for order, (s_name, s_val) in enumerate(specs, start=1):
                ProductSpec.objects.create(product=p, name=s_name, value=s_val, order=order)
            prods_map[slug] = p
            eval_products.append(p)

        self.stdout.write(f"Created {len(eval_products)} products.")

        self.stdout.write("2. Indexing with live Gemini API (Tags + Embeddings)...")
        stats = index_products(Product.objects.filter(id__in=[p.id for p in eval_products]), force=True, use_ai=True)
        self.stdout.write(f"Indexing complete! Stats: {stats}")
        invalidate_cache()

        index_data = _load_index()

        self.stdout.write("3. Running evaluation query suite...")

        test_cases = [
            # (query, [expected_slugs], [forbidden_slugs], description)
            ("headphone", ["eval-airpods", "eval-sony-xm5"], ["eval-bange-1908", "eval-anker-737", "eval-tplink-ax55"], "Meaning search for headphone"),
            ("airpods", ["eval-airpods"], ["eval-bange-1908", "eval-tplink-ax55"], "Direct brand product"),
            ("backpacks", ["eval-bange-1908", "eval-tomtoc-sleeve"], ["eval-airpods", "eval-sony-xm5"], "Plural stem bag search"),
            ("laptop backpack waterproof", ["eval-bange-1908"], ["eval-airpods"], "Multi-word coverage"),
            ("waterproof backpack laptop", ["eval-bange-1908"], ["eval-airpods"], "Order independence"),
            ("سماعات", ["eval-airpods", "eval-sony-xm5"], ["eval-bange-1908", "eval-tplink-ax55"], "Arabic generic audio"),
            ("ايربودز", ["eval-airpods"], ["eval-bange-1908"], "Arabic airpods transliteration"),
            ("شاحن سريع", ["eval-ugreen-65w", "eval-anker-737"], ["eval-bange-1908", "eval-airpods"], "Arabic fast charger"),
            ("كابل تايب سي", ["eval-baseus-cable"], ["eval-airpods", "eval-bange-1908"], "Arabic USB-C cable"),
            ("شنطة لابتوب", ["eval-bange-1908", "eval-tomtoc-sleeve"], ["eval-airpods", "eval-anker-737"], "Arabic laptop bag"),
            ("ماوس لاسلكي", ["eval-mx-master"], ["eval-airpods", "eval-bange-1908"], "Arabic wireless mouse"),
            ("راوتر", ["eval-tplink-ax55"], ["eval-airpods", "eval-bange-1908"], "Arabic router"),
            ("لابتوب جيمنج", ["eval-legion-5"], ["eval-bange-1908", "eval-airpods"], "Arabic gaming laptop"),
            ("power bank", ["eval-anker-737"], ["eval-airpods", "eval-tomtoc-sleeve"], "English power bank"),
            ("mechanical keyboard", ["eval-keychron-k2"], ["eval-airpods", "eval-bange-1908"], "English keyboard"),
            ("sony", ["eval-sony-xm5"], ["eval-bange-1908"], "Brand keyword"),
            ("wh-1000xm5", ["eval-sony-xm5"], ["eval-bange-1908"], "Exact model with dash"),
            ("wh1000xm5", ["eval-sony-xm5"], ["eval-bange-1908"], "Joined model token"),
            ("anc", ["eval-airpods", "eval-sony-xm5"], ["eval-bange-1908"], "Acronym negative check (no water resistance match)"),
        ]

        relevant_sims = []
        irrelevant_sims = []
        results_summary = []

        total_latency = 0.0

        for query, expected_slugs, forbidden_slugs, desc in test_cases:
            t0 = time.time()
            res = search(query)
            elapsed = (time.time() - t0) * 1000
            total_latency += elapsed

            returned_ids = res.ids
            expected_ids = [prods_map[s].id for s in expected_slugs if s in prods_map]
            forbidden_ids = [prods_map[s].id for s in forbidden_slugs if s in prods_map]

            top3 = returned_ids[:3]
            top10 = returned_ids[:10]

            # Check: at least one expected product in top 3
            pass_expected = any(eid in top3 for eid in expected_ids) if expected_ids else True
            # Check: no forbidden products in top 10
            pass_forbidden = not any(fid in top10 for fid in forbidden_ids)

            status = "PASS" if (pass_expected and pass_forbidden) else "FAIL"

            results_summary.append({
                "query": query,
                "status": status,
                "latency_ms": round(elapsed, 1),
                "top3": [Product.objects.get(id=pid).name[:25] for pid in top3],
                "expected": [prods_map[s].name[:20] for s in expected_slugs],
                "desc": desc,
            })

            # Collect similarities for calibration
            sem_hits = res.debug.get("sem_top10", [])
            sem_dict = dict(sem_hits)
            for eid in expected_ids:
                if eid in sem_dict:
                    relevant_sims.append(sem_dict[eid])
            for fid in forbidden_ids:
                if fid in sem_dict:
                    irrelevant_sims.append(sem_dict[fid])

        self.stdout.write("\n=================== EVALUATION RESULTS ===================")
        self.stdout.write(f"{'QUERY':<25} | {'STATUS':<6} | {'TIME(ms)':<8} | {'TOP 1 RESULT'}")
        self.stdout.write("-" * 75)
        
        all_passed = True
        for row in results_summary:
            top_str = row["top3"][0] if row["top3"] else "None"
            status_style = self.style.SUCCESS(row["status"]) if row["status"] == "PASS" else self.style.ERROR(row["status"])
            if row["status"] != "PASS":
                all_passed = False
            self.stdout.write(f"{row['query']:<25} | {status_style:<6} | {row['latency_ms']:<8} | {top_str}")

        # Measure cached latency
        self.stdout.write("\nMeasuring cached query embedding latency...")
        t_cache0 = time.time()
        for _ in range(5):
            search("headphone")
        cached_avg_ms = ((time.time() - t_cache0) / 5) * 1000
        self.stdout.write(f"Average cached search latency: {cached_avg_ms:.1f} ms")

        # Threshold calibration
        self.stdout.write("\n================ THRESHOLD CALIBRATION ================")
        if relevant_sims:
            min_rel = min(relevant_sims)
            avg_rel = sum(relevant_sims) / len(relevant_sims)
            self.stdout.write(f"Relevant pairs similarity: min={min_rel:.4f}, avg={avg_rel:.4f}, max={max(relevant_sims):.4f}")
        else:
            min_rel = 0.65

        if irrelevant_sims:
            max_irrel = max(irrelevant_sims)
            avg_irrel = sum(irrelevant_sims) / len(irrelevant_sims)
            self.stdout.write(f"Irrelevant pairs similarity: min={min(irrelevant_sims):.4f}, avg={avg_irrel:.4f}, max={max_irrel:.4f}")
        else:
            max_irrel = 0.55

        # Calibrated threshold midpoint
        calibrated = round((min_rel + max_irrel) / 2.0, 2)
        if calibrated < max_irrel:
            calibrated = round(max_irrel + 0.02, 2)

        self.stdout.write(self.style.SUCCESS(
            f"RECOMMENDED CALIBRATED SEARCH_SEMANTIC_MIN_SIM = {calibrated:.2f} "
            f"(Safely separates relevant >= {min_rel:.2f} from irrelevant <= {max_irrel:.2f})"
        ))
