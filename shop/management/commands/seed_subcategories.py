import re
from django.core.management.base import BaseCommand
from shop.models import Category, SubCategory, Product, Brand

DEFAULT_TAXONOMY = {
    # 1. Mobile Accessories (distinct from PC accessories)
    'mobile': [
        {
            'name': 'Fast Chargers & GaN',
            'name_ar': 'شواحن سريعة وGaN',
            'slug': 'chargers-gan',
            'icon': '⚡',
            'order': 1,
            'keywords': ['charger', 'gan', 'watt', '20w', '30w', '45w', '65w', '100w', '140w', 'شاحن', 'راس شاحن'],
        },
        {
            'name': 'Cables & Adapters',
            'name_ar': 'كابلات ومحولات',
            'slug': 'cables-adapters',
            'icon': '🔌',
            'order': 2,
            'keywords': ['cable', 'type-c', 'lightning', 'usb-c', 'aux', 'كابل', 'سلك', 'وصلة'],
        },
        {
            'name': 'Power Banks',
            'name_ar': 'باور بانك',
            'slug': 'power-banks',
            'icon': '🔋',
            'order': 3,
            'keywords': ['power bank', 'powerbank', 'باور بانك', 'بطارية متنقلة'],
        },
        {
            'name': 'Wireless Mics & Audio',
            'name_ar': 'مايكات وسماعات',
            'slug': 'wireless-mics-audio',
            'icon': '🎙️',
            'order': 4,
            'keywords': ['mic', 'microphone', 'lark', 'hollyland', 'earphone', 'headset', 'مايك', 'ميكروفون', 'سماعة'],
        },
        {
            'name': 'Holders & Car Mounts',
            'name_ar': 'حوامل موبايل وسيارة',
            'slug': 'holders-mounts',
            'icon': '📱',
            'order': 5,
            'keywords': ['holder', 'car mount', 'car charger', 'stand', 'حامل', 'حامل سيارة'],
        },
    ],
    # 2. Computer Accessories
    'accessor': [
        {
            'name': 'Mice & Pointers',
            'name_ar': 'ماوسات',
            'slug': 'mice',
            'icon': '🖱️',
            'order': 1,
            'keywords': ['mouse', 'mice', 'trackpad', 'pointer', 'ماوس', 'فأرة'],
        },
        {
            'name': 'Keyboards',
            'name_ar': 'لوحات مفاتيح وكيبورد',
            'slug': 'keyboards',
            'icon': '⌨️',
            'order': 2,
            'keywords': ['keyboard', 'keychron', 'mechanical', 'كيبورد', 'لوحة مفاتيح'],
        },
        {
            'name': 'Headsets & Audio',
            'name_ar': 'سماعات وصوتيات',
            'slug': 'headsets',
            'icon': '🎧',
            'order': 3,
            'keywords': ['headset', 'headphone', 'earphone', 'airpod', 'earbud', 'audio', 'sound', 'سماعة', 'سماعات'],
        },
        {
            'name': 'Hubs & Adapters',
            'name_ar': 'محولات ووصلات Hubs',
            'slug': 'hubs-adapters',
            'icon': '🔌',
            'order': 4,
            'keywords': ['hub', 'dock', 'adapter', 'dongle', 'converter', 'type-c', 'hdmi', 'محول', 'وصلة', 'هب'],
        },
        {
            'name': 'Chargers & Power',
            'name_ar': 'شواحن وكابلات',
            'slug': 'chargers-power',
            'icon': '🔋',
            'order': 5,
            'keywords': ['charger', 'cable', 'power bank', 'gan', 'magsafe', 'watt', 'شاحن', 'كابل', 'باور'],
        },
        {
            'name': 'Stands & Mounts',
            'name_ar': 'حوامل وستاندات',
            'slug': 'stands-mounts',
            'icon': '🪵',
            'order': 6,
            'keywords': ['stand', 'mount', 'holder', 'riser', 'حامل', 'ستاند'],
        },
    ],
    'laptop': [
        {
            'name': 'Gaming Laptops',
            'name_ar': 'لابتوبات ألعاب وجيمنج',
            'slug': 'gaming-laptops',
            'icon': '🎮',
            'order': 1,
            'keywords': ['gaming', 'tuf', 'rog', 'legion', 'predator', 'alienware', 'victus', 'nitro', 'rtx', 'geforce', 'جيمنج', 'ألعاب'],
        },
        {
            'name': 'Ultrabooks & Business',
            'name_ar': 'أجهزة خفيفة وبيزنس',
            'slug': 'ultrabooks',
            'icon': '💼',
            'order': 2,
            'keywords': ['thinkpad', 'zenbook', 'air', 'xps', 'spectre', 'swift', 'slim', 'elitebook', 'بيزنس', 'خفيف', 'ألترابوك'],
        },
        {
            'name': 'Workstations & Creator',
            'name_ar': 'مونتاج وورك ستيشن',
            'slug': 'workstations',
            'icon': '🎨',
            'order': 3,
            'keywords': ['pro 14', 'pro 16', 'macbook pro', 'precision', 'creator', 'proart', 'zbook', 'studio', 'workstation', 'مونتاج', 'جرافيك'],
        },
        {
            'name': 'Student & Everyday',
            'name_ar': 'دراسة واستخدام يومي',
            'slug': 'student-laptops',
            'icon': '📚',
            'order': 4,
            'keywords': ['ideapad', 'inspiron', 'vivobook', 'pavilion', 'aspire', 'دراسة', 'جامعة'],
        },
    ],
    'sleeve': [
        {
            'name': 'Backpacks',
            'name_ar': 'شنط ظهر',
            'slug': 'backpacks',
            'icon': '🎒',
            'order': 1,
            'keywords': ['backpack', 'ظهر', 'حقيبة ظهر'],
        },
        {
            'name': 'Shoulder & Crossbody',
            'name_ar': 'شنط كتف وكروس',
            'slug': 'shoulder-bags',
            'icon': '💼',
            'order': 2,
            'keywords': ['shoulder', 'crossbody', 'messenger', 'briefcase', 'كتف', 'كروس', 'يد'],
        },
        {
            'name': 'Laptop Sleeves',
            'name_ar': 'جرابات وحافظات',
            'slug': 'laptop-sleeves',
            'icon': '💻',
            'order': 3,
            'keywords': ['sleeve', 'pouch', 'cover', 'case', 'جراب', 'حافظة', 'كفر'],
        },
    ],
    'bag': [
        {
            'name': 'Backpacks',
            'name_ar': 'شنط ظهر',
            'slug': 'backpacks',
            'icon': '🎒',
            'order': 1,
            'keywords': ['backpack', 'ظهر', 'حقيبة ظهر'],
        },
        {
            'name': 'Shoulder & Crossbody',
            'name_ar': 'شنط كتف وكروس',
            'slug': 'shoulder-bags',
            'icon': '💼',
            'order': 2,
            'keywords': ['shoulder', 'crossbody', 'messenger', 'briefcase', 'كتف', 'كروس', 'يد'],
        },
        {
            'name': 'Laptop Sleeves',
            'name_ar': 'جرابات وحافظات',
            'slug': 'laptop-sleeves',
            'icon': '💻',
            'order': 3,
            'keywords': ['sleeve', 'pouch', 'cover', 'case', 'جراب', 'حافظة', 'كفر'],
        },
    ],
}

CANONICAL_BRANDS = {
    'ugreen': ('Ugreen', 'ugreen'),
    'u green': ('Ugreen', 'ugreen'),
    'u-green': ('Ugreen', 'ugreen'),
    'anker': ('Anker', 'anker'),
    'bange': ('Bange', 'bange'),
    'apple': ('Apple', 'apple'),
    'lenovo': ('Lenovo', 'lenovo'),
    'dell': ('Dell', 'dell'),
    'hp': ('HP', 'hp'),
    'asus': ('ASUS', 'asus'),
    'logitech': ('Logitech', 'logitech'),
    'logetich': ('Logitech', 'logitech'),
    'tp-link': ('TP-Link', 'tp-link'),
    'tp link': ('TP-Link', 'tp-link'),
    'tplink': ('TP-Link', 'tp-link'),
    'acefast': ('Acefast', 'acefast'),
    'chantria': ('Chantria', 'chantria'),
    'hollyland': ('Hollyland', 'hollyland'),
    'joyroom': ('Joyroom', 'joyroom'),
    'mcdodo': ('Mcdodo', 'mcdodo'),
    'baseus': ('Baseus', 'baseus'),
    'wiwu': ('WiWU', 'wiwu'),
    'arctic hunter': ('Arctic Hunter', 'arctic-hunter'),
    'poso': ('Poso', 'poso'),
    'ozuko': ('Ozuko', 'ozuko'),
    'samsung': ('Samsung', 'samsung'),
    'k&f': ('K&F Concept', 'kf-concept'),
    'k&f concept': ('K&F Concept', 'kf-concept'),
    'veikk': ('VEIKK', 'veikk'),
    'huion': ('Huion', 'huion'),
    'wacom': ('Wacom', 'wacom'),
}


class Command(BaseCommand):
    help = "Seed standard SubCategories, deduplicate/normalize brands, and accurately classify products."

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("Starting SubCategory Seeding & Brand Deduplication")
        self.stdout.write("==================================================")

        # ------------------------------------------------------------------
        # 1. Clean up bogus subcategories on Mobile Accessories
        # ------------------------------------------------------------------
        mobile_cats = Category.objects.filter(slug__icontains='mobile')
        for m_cat in mobile_cats:
            bogus_subs = SubCategory.objects.filter(category=m_cat, slug__in=['mice', 'keyboards'])
            if bogus_subs.exists():
                for bs in bogus_subs:
                    # Unassign products first so they can be reclassified
                    unassigned_count = Product.objects.filter(subcategory=bs).update(subcategory=None)
                    self.stdout.write(f"  - Removed bogus subcategory [{bs.name}] from [{m_cat.name}] (unassigned {unassigned_count} prods)")
                    bs.delete()

        # ------------------------------------------------------------------
        # 2. Seed Subcategories per Category Taxonomy
        # ------------------------------------------------------------------
        total_created_subs = 0
        total_classified_prods = 0

        categories = Category.objects.all()
        for category in categories:
            cat_slug = category.slug.lower()
            cat_name = category.name.lower()

            matched_preset = None
            for key, preset_list in DEFAULT_TAXONOMY.items():
                if key in cat_slug or key in cat_name:
                    matched_preset = preset_list
                    break

            if not matched_preset:
                matched_preset = [
                    {'name': f'General {category.name}', 'name_ar': f'{category.name} عام', 'slug': f'general-{category.slug}', 'icon': '⚡', 'order': 1, 'keywords': [category.name.lower()]}
                ]

            subcat_objs = []
            for sub_def in matched_preset:
                subcat, created = SubCategory.objects.get_or_create(
                    category=category,
                    slug=sub_def['slug'],
                    defaults={
                        'name': sub_def['name'],
                        'name_ar': sub_def.get('name_ar', ''),
                        'icon': sub_def.get('icon', '⚡'),
                        'order': sub_def.get('order', 0),
                    }
                )
                if created:
                    total_created_subs += 1
                    self.stdout.write(f"  + Created SubCategory: [{category.name}] -> {subcat.name}")
                subcat_objs.append((subcat, sub_def.get('keywords', [])))

            # Auto-classify unassigned products based on search_text
            cat_products = Product.objects.filter(category=category, subcategory__isnull=True)
            for product in cat_products:
                search_text = f"{product.name} {product.description}".lower()
                for spec in product.specs.all():
                    search_text += f" {spec.name} {spec.value}".lower()

                assigned_sub = None
                for subcat, keywords in subcat_objs:
                    for kw in keywords:
                        if re.search(r'\b' + re.escape(kw.lower()) + r'\b', search_text, re.IGNORECASE) or kw.lower() in search_text:
                            assigned_sub = subcat
                            break
                    if assigned_sub:
                        break

                if assigned_sub:
                    product.subcategory = assigned_sub
                    product.save(update_fields=['subcategory'])
                    total_classified_prods += 1
                    self.stdout.write(f"    Assigned '{product.name[:35]}...' -> {assigned_sub.name}")

        # ------------------------------------------------------------------
        # 3. Deduplicate and Normalize Brands
        # ------------------------------------------------------------------
        self.stdout.write("\nNormalizing & Deduplicating Brands...")
        merged_brands_count = 0

        # Step 3A: Merge known canonical aliases
        all_brands = list(Brand.objects.all())
        brand_by_canonical = {}

        for b in all_brands:
            norm_key = b.name.strip().lower()
            canonical_info = CANONICAL_BRANDS.get(norm_key) or CANONICAL_BRANDS.get(b.slug.strip().lower())
            
            if canonical_info:
                canon_name, canon_slug = canonical_info
            else:
                # Standard Title Case for unmapped brands
                canon_name = b.name.strip().title() if (b.name.islower() or b.name.isupper()) else b.name.strip()
                canon_slug = b.slug.strip().lower()

            target_key = canon_slug

            if target_key not in brand_by_canonical:
                # Update current brand to canonical name and slug if needed
                if b.name != canon_name or b.slug != canon_slug:
                    # Check if another brand already holds this slug
                    conflict = Brand.objects.filter(slug=canon_slug).exclude(id=b.id).first()
                    if conflict:
                        # Will be merged in the else branch below
                        brand_by_canonical[target_key] = conflict
                    else:
                        b.name = canon_name
                        b.slug = canon_slug
                        b.save(update_fields=['name', 'slug'])
                        self.stdout.write(f"  * Normalized Brand: -> {canon_name} ({canon_slug})")
                brand_by_canonical[target_key] = b
            else:
                primary_brand = brand_by_canonical[target_key]
                if primary_brand.id != b.id:
                    # Migrate products to primary brand
                    prod_count = Product.objects.filter(brand=b).update(brand=primary_brand)
                    # Migrate categories
                    for cat in b.categories.all():
                        cat.brands.add(primary_brand)
                    self.stdout.write(f"  * Merged duplicate brand '{b.name}' ({b.id}) into '{primary_brand.name}' ({primary_brand.id}) [{prod_count} prods migrated]")
                    b.delete()
                    merged_brands_count += 1

        # Step 3B: Ensure top brands exist
        for canon_name, canon_slug in CANONICAL_BRANDS.values():
            Brand.objects.get_or_create(slug=canon_slug, defaults={'name': canon_name})

        # Step 3C: Auto-link unassigned products to brands
        linked_brands = 0
        all_active_brands = list(Brand.objects.all())
        for p in Product.objects.filter(brand__isnull=True):
            p_name_lower = p.name.lower()
            for b_obj in all_active_brands:
                b_name_lower = b_obj.name.lower()
                if (len(b_name_lower) >= 3 and (b_name_lower in p_name_lower or b_obj.slug in p_name_lower)):
                    p.brand = b_obj
                    p.save(update_fields=['brand'])
                    linked_brands += 1
                    break

        self.stdout.write(
            f"\nFinished! Created {total_created_subs} subcategories, merged {merged_brands_count} duplicate brands, classified {total_classified_prods} products, and linked {linked_brands} unbranded products."
        )
