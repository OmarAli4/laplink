import re
from django.core.management.base import BaseCommand
from shop.models import Category, SubCategory, Product, Brand

DEFAULT_TAXONOMY = {
    'apple': [
        {
            'name': 'iPad & Apple Devices',
            'name_ar': 'أجهزة آيباد وأبل',
            'slug': 'ipad-devices',
            'icon': '📱',
            'order': 1,
            'keywords': ['ipad', 'apple', 'a16', 'آيباد', 'ايباد', 'أبل', 'ابل'],
        },
    ],
    'laptop': [
        {
            'name': 'iPad & Apple Devices',
            'name_ar': 'أجهزة آيباد وأبل',
            'slug': 'ipad-devices',
            'icon': '📱',
            'order': 1,
            'keywords': ['ipad', 'apple', 'a16', 'آيباد', 'ايباد', 'أبل', 'ابل'],
        },
    ],
    'bag': [
        {
            'name': 'Crossbody & Chest Bags',
            'name_ar': 'شنط كتف وكروس',
            'slug': 'shoulder-bags',
            'icon': '👜',
            'order': 3,
            'keywords': ['crossbody', 'sling', 'chest', 'shoulder', 'messenger', 'g65', 'g66', 'xb00345', '7211', 'كتف', 'كروس', 'صدر'],
        },
        {
            'name': 'Laptop Sleeves & Handbags',
            'name_ar': 'جرابات وحافظات لابتوب',
            'slug': 'laptop-sleeves',
            'icon': '💼',
            'order': 2,
            'keywords': ['sleeve', 'case', 'pouch', 'briefcase', 'handbag', 'chantria', 'elite', 'جراب', 'حافظة', 'يد'],
        },
        {
            'name': 'Laptop Backpacks',
            'name_ar': 'شنط ظهر للابتوب',
            'slug': 'backpacks',
            'icon': '🎒',
            'order': 1,
            'keywords': ['backpack', 'back pack', 'rucksack', 'bange', 'arctic hunter', 'coolbell', 'شنطة ظهر', 'حقيبة ظهر', 'باك باك', 'bag'],
        },
    ],
    'computer': [
        {
            'name': 'Keyboards & Combos',
            'name_ar': 'كيبورد وماوس كومبو',
            'slug': 'keyboards',
            'icon': '⌨️',
            'order': 2,
            'keywords': ['keyboard', 'combo', 'mk120', 'mk220', 'mk235', 'mk270', 'mk295', 'mk345', '8000m', '9010m', 'touchpad', 'كيبورد', 'لوحة مفاتيح'],
        },
        {
            'name': 'Mice & Presenters',
            'name_ar': 'ماوسات ومؤشرات عرض',
            'slug': 'mice',
            'icon': '🖱️',
            'order': 1,
            'keywords': ['mouse', 'mice', 'presenter', 'presentation', 'r400', 'r500', 'm170', 'm171', 'm185', 'm190', 'm240', 'm330', 'g102', 'g305', 'g502', 'm650', 'b30', 'm20', '1620', '3510', 'n100', 'cw905', 'ماوس', 'فأرة'],
        },
        {
            'name': 'Laptop & Desk Stands',
            'name_ar': 'حوامل لابتوب ومكتب',
            'slug': 'stands-mounts',
            'icon': '🪵',
            'order': 6,
            'keywords': ['stand', 'riser', 'cooling pad', 'cooler', 'sn-539', 'c296', '80432', '90416', 'حامل', 'ستاند', 'مبرد'],
        },
        {
            'name': 'HDMI & Display Cables',
            'name_ar': 'كابلات شاشات وHDMI',
            'slug': 'display-cables',
            'icon': '🖥️',
            'order': 4,
            'keywords': ['hdmi', 'displayport', 'dp ', 'vga', 'dvi', 'rs232', 'serial', 'printer cable', 'extension cable', '10335', '10133', '20124', 'switch 3 in 1', 'كابل شاشة'],
        },
        {
            'name': 'Headsets, Speakers & Studio Mics',
            'name_ar': 'سماعات، سبيكر ومايكات استوديو',
            'slug': 'headsets',
            'icon': '🎧',
            'order': 5,
            'keywords': ['headset', 'headphone', 'speaker', 'soundbar', 'soundcore', 'flare', 'motion', 'powerconf', 'webcam', 'c200', 'maono', 'a04', 'pd200x', 'pd100u', 'h111', 'h390', 'ge-h105', 'سماعة', 'سبيكر', 'مايك', 'ويب كام'],
        },
        {
            'name': 'USB-C Hubs, Docks & Storage',
            'name_ar': 'موزعات USB-C ووصلات هارد',
            'slug': 'hubs-adapters',
            'icon': '🔌',
            'order': 3,
            'keywords': ['hub', 'dock', 'multiport', 'sata', 'ssd', 'hdd', 'enclosure', 'card reader', 'sound card', 'dongle', 'transmitter', 'receiver', 'cm868', 'onten', 'revodok', 'هاب', 'موزع', 'راك'],
        },
    ],
    'mobile': [
        {
            'name': 'Power Banks',
            'name_ar': 'باور بانك',
            'slug': 'power-banks',
            'icon': '🔋',
            'order': 3,
            'keywords': ['power bank', 'powerbank', 'zolo', '10000mah', '20000mah', 'magsafe battery', 'باور بانك', 'بطارية'],
        },
        {
            'name': 'Car Chargers & Holders',
            'name_ar': 'شواحن وحوامل السيارة',
            'slug': 'holders-mounts',
            'icon': '🚗',
            'order': 6,
            'keywords': ['car charger', 'car holder', 'car inverter', 'vc07', 'magnet holder', 'c82', 'c251', 'c87', 'glass holder', 'b13', '35629', '50698', 'a2727', 'sn-607', 'سيارة', 'حامل موبايل'],
        },
        {
            'name': 'Gimbals, Tripods & Lighting',
            'name_ar': 'جيمبال، ترايبود وإضاءة تصوير',
            'slug': 'content-creation',
            'icon': '📸',
            'order': 5,
            'keywords': ['osmo', 'gimbal', 'tripod', 'selfie', 'ring light', 'softbox', 'plokama', 'p10', 'p12', 'p19', 'p7', 'z15', 'gx9', 'ss-9', 'live-1', '1280', '1680', '3398', '997s', '998s', '999s', 'k5', 'u20', 'w80', 'ترايبود', 'جيمبال', 'رينج لايت', 'سيلفي'],
        },
        {
            'name': 'Earbuds & Wireless Mics',
            'name_ar': 'إيربودز ومايكات لاسلكية',
            'slug': 'wireless-mics-audio',
            'icon': '🎙️',
            'order': 4,
            'keywords': ['earbud', 'airpod', 'tws', 'r50i', 'r60i', 'u2i', 'hitune', 'buds4', 'lark', 'hollyland', 'dji mic', 'lavalier', 'microphone', 'wm1', 'g20', 'gt12', 'j13', 'k9', 's22', 'سماعة', 'إيربودز', 'ايربودز', 'مايك', 'ميكروفون'],
        },
        {
            'name': 'Fast Chargers & GaN',
            'name_ar': 'شواحن سريعة وGaN',
            'slug': 'chargers-gan',
            'icon': '⚡',
            'order': 1,
            'keywords': ['charger', 'gan', 'nexode', 'wall charger', 'powerport', 'nano', 'acefast a', 'mcdodo ch', 'joyroom tc', 'sn-411', 'sn-403', 'sn-538', 'sn-547', 'w02', 'mc09', 'universal adapter', 'magsafe', '35998', 'شاحن', 'راس شاحن'],
        },
        {
            'name': 'Charging & Audio Cables',
            'name_ar': 'كابلات شحن وصوت ومحولات OTG',
            'slug': 'cables-adapters',
            'icon': '🔌',
            'order': 2,
            'keywords': ['cable', 'cord', 'lightning', 'type-c', 'type c', 'usb-c', 'micro usb', 'aux', 'otg', 'splitter', 'converter', 'watch cable', 'ca-', 'كابل', 'وصلة'],
        },
    ],
    'network': [
        {
            'name': 'Network Switches',
            'name_ar': 'سويتشات وموزعات شبكة',
            'slug': 'network-switches',
            'icon': '🖧',
            'order': 3,
            'keywords': ['switch', 'ls1005', 'ls1008', 'sf1005', 'tl-sg', 'سويتش'],
        },
        {
            'name': 'Range Extenders & Powerline',
            'name_ar': 'مقويات شبكة الواي فاي',
            'slug': 'range-extenders',
            'icon': '📶',
            'order': 2,
            'keywords': ['extender', 'repeater', 're200', 're205', 're315', 'wa850re', 'wa855re', 'wpa4220', 'powerline', 'مقوي'],
        },
        {
            'name': 'USB Wi-Fi Adapters & LAN Cables',
            'name_ar': 'كروت واي فاي وكابلات نت',
            'slug': 'network-adapters',
            'icon': '🔌',
            'order': 4,
            'keywords': ['adapter', 'usb', 'nano', 'wn725n', 'wn823n', 'wn722n', 'cat6', 'cat7', 'rj45', 'ethernet', 'patch cable', '11262', '50307', '50737', 'كارت واي فاي', 'كابل نت'],
        },
        {
            'name': 'Wi-Fi Routers & Mesh',
            'name_ar': 'راوترات وشبكات Mesh',
            'slug': 'wifi-routers',
            'icon': '📡',
            'order': 1,
            'keywords': ['router', 'deco', 'mesh', 'archer', 'modem', 'vr300', 'w9950', 'wr840n', 'c24', 'c50', 'c54', 'راوتر'],
        },
    ],
    'graphic': [
        {
            'name': 'Pen Displays & Stylus Pens',
            'name_ar': 'شاشات وأقلام الرسم',
            'slug': 'pen-displays',
            'icon': '🖊️',
            'order': 2,
            'keywords': ['kamvas', 'display', 'stylus', 'pencil', 'pen', '121', 'شاشة رسم', 'قلم'],
        },
        {
            'name': 'Digital Drawing Tablets',
            'name_ar': 'ألواح الرسم الجرافيكي',
            'slug': 'drawing-tablets',
            'icon': '🎨',
            'order': 1,
            'keywords': ['tablet', 'inspiroy', 'hs64', 'h640p', 'h950p', 'h430p', 'h610x', 'hs610', 'hs611', 'h320m', 'veikk', 'a30', 'a50', 'wacom', 'ctl-672', 'تابلت رسم'],
        },
    ],
}

CATEGORY_METADATA = {
    'apple': {'name': 'iPad & Apple', 'name_ar': 'آيباد وأجهزة أبل'},
    'laptop': {'name': 'iPad & Apple', 'name_ar': 'آيباد وأجهزة أبل'},
    'bags': {'name': 'Laptop Bags & Sleeves', 'name_ar': 'شنط وجرابات اللابتوب'},
    'computer-accessories': {'name': 'Computer & Desk Accessories', 'name_ar': 'إكسسوارات الكمبيوتر والمكتب'},
    'mobile-accessories': {'name': 'Mobile, Charging & Content Gear', 'name_ar': 'إكسسوارات الموبايل والشحن والتصوير'},
    'network': {'name': 'Networking & Wi-Fi', 'name_ar': 'الشبكات والراوترات'},
    'graphic-tablet': {'name': 'Graphic Drawing Tablets', 'name_ar': 'تابلت الرسم والجرافيك'},
}

CANONICAL_BRANDS = {
    'ipad': ('Apple', 'apple'),
    'apple': ('Apple', 'apple'),
    'green': ('Ugreen', 'ugreen'),
    'u green': ('Ugreen', 'ugreen'),
    'u-green': ('Ugreen', 'ugreen'),
    'ugreen': ('Ugreen', 'ugreen'),
    'velkk': ('VEIKK', 'veikk'),
    'veikk': ('VEIKK', 'veikk'),
    'jooyroom': ('Joyroom', 'joyroom'),
    'joyroom': ('Joyroom', 'joyroom'),
    'logetich': ('Logitech', 'logitech'),
    'logitech': ('Logitech', 'logitech'),
    'rapo': ('Rapoo', 'rapoo'),
    'rapoo': ('Rapoo', 'rapoo'),
    'dji': ('DJI', 'dji'),
    'anker': ('Anker', 'anker'),
    'bange': ('Bange', 'bange'),
    'lenovo': ('Lenovo', 'lenovo'),
    'dell': ('Dell', 'dell'),
    'hp': ('HP', 'hp'),
    'asus': ('ASUS', 'asus'),
    'tp-link': ('TP-Link', 'tp-link'),
    'tp link': ('TP-Link', 'tp-link'),
    'tplink': ('TP-Link', 'tp-link'),
    'acefast': ('Acefast', 'acefast'),
    'chantria': ('Chantria', 'chantria'),
    'hollyland': ('Hollyland', 'hollyland'),
    'mcdodo': ('Mcdodo', 'mcdodo'),
    'baseus': ('Baseus', 'baseus'),
    'wiwu': ('WiWU', 'wiwu'),
    'arctic hunter': ('Arctic Hunter', 'arctic-hunter'),
    'poso': ('Poso', 'poso'),
    'ozuko': ('Ozuko', 'ozuko'),
    'samsung': ('Samsung', 'samsung'),
    'k&f': ('K&F Concept', 'kf-concept'),
    'k&f concept': ('K&F Concept', 'kf-concept'),
    'huion': ('Huion', 'huion'),
    'wacom': ('Wacom', 'wacom'),
    'maono': ('MAONO', 'maono'),
    'plokama': ('PLOKAMA', 'plokama'),
    'snzou': ('SNZOU', 'snzou'),
    'coolbell': ('CoolBell', 'coolbell'),
    'recci': ('Recci', 'recci'),
    'jedel': ('Jedel', 'jedel'),
    'onikuma': ('Onikuma', 'onikuma'),
    'onten': ('Onten', 'onten'),
}


class Command(BaseCommand):
    help = "Seed standard SubCategories, migrate misclassified products, deduplicate brands, and accurately classify all 356 products."

    def handle(self, *args, **options):
        self.stdout.write("==================================================")
        self.stdout.write("Starting 356-Product Taxonomy Overhaul & Seeding")
        self.stdout.write("==================================================")

        # ------------------------------------------------------------------
        # 1. Normalize Categories and Fix Misclassified Products
        # ------------------------------------------------------------------
        # A) Standardize Category Names & Arabic Names
        for cat in Category.objects.all():
            cat_slug_lower = cat.slug.lower()
            for key, meta in CATEGORY_METADATA.items():
                if key == cat_slug_lower or key in cat_slug_lower:
                    cat.name = meta['name']
                    cat.name_ar = meta['name_ar']
                    cat.save(update_fields=['name', 'name_ar'])
                    self.stdout.write(f"  * Normalized Category: [{cat.slug}] -> {cat.name}")
                    break

        cat_network = Category.objects.filter(slug__iexact='network').first()
        cat_mobile = Category.objects.filter(slug__iexact='mobile-accessories').first()
        cat_computer = Category.objects.filter(slug__iexact='computer-accessories').first()
        cat_apple = Category.objects.filter(slug__iexact='apple').first()

        # B) Move Network Ethernet Cables [53, 72, 73] to Network
        if cat_network:
            moved_net = Product.objects.filter(id__in=[53, 72, 73]).update(category=cat_network, subcategory=None)
            self.stdout.write(f"  -> Moved {moved_net} ethernet cables to [Network]")

        # C) Move Mobile/GaN Chargers [54, 60, 61, 66, 67, 81, 83, 122] to Mobile Accessories
        if cat_mobile:
            moved_mob = Product.objects.filter(id__in=[54, 60, 61, 66, 67, 81, 83, 122]).update(category=cat_mobile, subcategory=None)
            self.stdout.write(f"  -> Moved {moved_mob} chargers/earbuds to [Mobile Accessories]")

        # D) Move Computer Mice/Keyboards/Cables/Stands [93, 96, 98, 311, 312, 313, 314, 315, 316, 382] to Computer Accessories
        if cat_computer:
            moved_comp = Product.objects.filter(id__in=[93, 96, 98, 311, 312, 313, 314, 315, 316, 382]).update(category=cat_computer, subcategory=None)
            self.stdout.write(f"  -> Moved {moved_comp} mice/keyboards/cables to [Computer Accessories]")

        # E) Ensure iPad Product #304 is correctly attributed to Apple brand & APPLE category
        p304 = Product.objects.filter(id=304).first()
        if p304:
            apple_brand, _ = Brand.objects.get_or_create(slug='apple', defaults={'name': 'Apple'})
            p304.brand = apple_brand
            if cat_apple:
                p304.category = cat_apple
            p304.search_tags = 'apple ipad a16 tablet 11-inch wifi آيباد أبل ايباد تابلت'
            p304.save(update_fields=['brand', 'category', 'search_tags'])
            self.stdout.write(f"  -> Successfully verified Product #304 [Apple iPad A16] with Brand [Apple]")

        # ------------------------------------------------------------------
        # 2. Seed Subcategories per Category Taxonomy and Clean Up Stale Ones
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
                    {'name': f'General {category.name}', 'name_ar': f'{category.name_ar or category.name} عام', 'slug': f'general-{category.slug.lower()}', 'icon': '⚡', 'order': 1, 'keywords': [category.name.lower()]}
                ]

            valid_slugs = [s['slug'] for s in matched_preset]

            # Unassign and delete stale subcategories for this category
            stale_subs = SubCategory.objects.filter(category=category).exclude(slug__in=valid_slugs)
            if stale_subs.exists():
                for ss in stale_subs:
                    unassigned = Product.objects.filter(subcategory=ss).update(subcategory=None)
                    self.stdout.write(f"  - Deleted stale subcategory [{ss.name}] from [{category.name}] ({unassigned} prods unassigned)")
                    ss.delete()

            # Ensure all valid subcategories exist and have correct name, name_ar, icon, order
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
                if not created:
                    subcat.name = sub_def['name']
                    subcat.name_ar = sub_def.get('name_ar', '')
                    subcat.icon = sub_def.get('icon', '⚡')
                    subcat.order = sub_def.get('order', 0)
                    subcat.save(update_fields=['name', 'name_ar', 'icon', 'order'])
                else:
                    total_created_subs += 1
                    self.stdout.write(f"  + Created SubCategory: [{category.slug}] -> {subcat.name}")

                subcat_objs.append((subcat, sub_def.get('keywords', [])))

            # Re-classify all products of this category to ensure accurate mapping
            cat_products = Product.objects.filter(category=category)
            for product in cat_products:
                search_text = f"{product.name} {product.description}".lower()
                for spec in product.specs.all():
                    search_text += f" {spec.name} {spec.value}".lower()

                assigned_sub = None
                for subcat, keywords in subcat_objs:
                    for kw in keywords:
                        kw_lower = kw.lower()
                        # Match word boundaries or substring
                        if re.search(r'(?:^|[\s\-_/])' + re.escape(kw_lower) + r'(?:$|[\s\-_/])', search_text) or kw_lower in search_text:
                            assigned_sub = subcat
                            break
                    if assigned_sub:
                        break

                # Fallback to the first subcategory in preset if none matched
                if not assigned_sub and subcat_objs:
                    assigned_sub = subcat_objs[0][0]

                if assigned_sub and product.subcategory_id != assigned_sub.id:
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
                canon_name = b.name.strip().title() if (b.name.islower() or b.name.isupper()) else b.name.strip()
                canon_slug = b.slug.strip().lower()

            target_key = canon_slug

            if target_key not in brand_by_canonical:
                if b.name != canon_name or b.slug != canon_slug:
                    conflict = Brand.objects.filter(slug=canon_slug).exclude(id=b.id).first()
                    if conflict:
                        brand_by_canonical[target_key] = conflict
                        # Merge b into conflict
                        Product.objects.filter(brand=b).update(brand=conflict)
                        for cat in b.categories.all():
                            cat.brands.add(conflict)
                        self.stdout.write(f"  * Merged duplicate brand '{b.name}' ({b.id}) into existing '{conflict.name}' ({conflict.id})")
                        b.delete()
                        merged_brands_count += 1
                        continue
                    else:
                        b.name = canon_name
                        b.slug = canon_slug
                        b.save(update_fields=['name', 'slug'])
                        self.stdout.write(f"  * Normalized Brand: -> {canon_name} ({canon_slug})")
                brand_by_canonical[target_key] = b
            else:
                primary_brand = brand_by_canonical[target_key]
                if primary_brand.id != b.id:
                    prod_count = Product.objects.filter(brand=b).update(brand=primary_brand)
                    for cat in b.categories.all():
                        cat.brands.add(primary_brand)
                    self.stdout.write(f"  * Merged duplicate brand '{b.name}' ({b.id}) into '{primary_brand.name}' ({primary_brand.id}) [{prod_count} prods migrated]")
                    b.delete()
                    merged_brands_count += 1

        # Step 3B: Ensure top canonical brands exist
        for canon_name, canon_slug in CANONICAL_BRANDS.values():
            Brand.objects.get_or_create(slug=canon_slug, defaults={'name': canon_name})

        # Step 3C: Auto-link unassigned products to brands
        linked_brands = 0
        all_active_brands = list(Brand.objects.all())
        for p in Product.objects.filter(brand__isnull=True):
            p_name_lower = p.name.lower()
            for b_obj in all_active_brands:
                b_name_lower = b_obj.name.lower()
                if len(b_name_lower) >= 3 and (b_name_lower in p_name_lower or b_obj.slug in p_name_lower):
                    p.brand = b_obj
                    p.save(update_fields=['brand'])
                    linked_brands += 1
                    break

        self.stdout.write(
            f"\nFinished! Created {total_created_subs} subcategories, merged {merged_brands_count} duplicate brands, classified/reclassified {total_classified_prods} products, and linked {linked_brands} unbranded products."
        )
