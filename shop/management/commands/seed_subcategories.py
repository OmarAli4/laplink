import re
from django.core.management.base import BaseCommand
from shop.models import Category, SubCategory, Product

DEFAULT_TAXONOMY = {
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

class Command(BaseCommand):
    help = "Seed standard SubCategories for store Categories and auto-link matching products."

    def handle(self, *args, **options):
        self.stdout.write("Starting SubCategory seeding & auto-classification...")
        total_created_subs = 0
        total_classified_prods = 0

        categories = Category.objects.all()
        if not categories.exists():
            self.stdout.write("No categories found in database.")
            return

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

            cat_products = Product.objects.filter(category=category)
            for product in cat_products:
                if product.subcategory:
                    continue

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

                if not assigned_sub and subcat_objs:
                    assigned_sub = subcat_objs[0][0]

                if assigned_sub:
                    product.subcategory = assigned_sub
                    product.save(update_fields=['subcategory'])
                    total_classified_prods += 1
                    self.stdout.write(f"    Assigned '{product.name}' -> {assigned_sub.name}")

        self.stdout.write(
            f"\nFinished! Created {total_created_subs} subcategories and classified {total_classified_prods} products."
        )