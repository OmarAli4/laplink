from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from shop.models import Category, Product
from coupons.models import Coupon


class Command(BaseCommand):
    help = 'Seeds the database with sample electronics products and a test coupon'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Categories
        categories_data = [
            ('Smartphones', 'smartphones'),
            ('Laptops', 'laptops'),
            ('Headphones', 'headphones'),
            ('Cameras', 'cameras'),
            ('Gaming', 'gaming'),
            ('Accessories', 'accessories'),
        ]

        categories = {}
        for name, slug in categories_data:
            cat, created = Category.objects.get_or_create(name=name, slug=slug)
            categories[slug] = cat
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: Category "{name}"')

        # Products
        products_data = [
            # Smartphones
            ('iPhone 16 Pro Max', 'iphone-16-pro-max', 'smartphones',
             Decimal('1199.99'),
             'The most advanced iPhone ever. Featuring the A18 Pro chip, a 48MP camera system, titanium design, and all-day battery life.'),
            ('Samsung Galaxy S25 Ultra', 'samsung-galaxy-s25-ultra', 'smartphones',
             Decimal('1299.99'),
             'Galaxy AI built in. Titanium frame, 200MP camera, S Pen included. The ultimate Galaxy experience.'),
            ('Google Pixel 9 Pro', 'google-pixel-9-pro', 'smartphones',
             Decimal('999.00'),
             'The best of Google AI in a phone. Tensor G4 chip, Magic Eraser, and 7 years of updates.'),

            # Laptops
            ('MacBook Pro 16" M4 Max', 'macbook-pro-16-m4-max', 'laptops',
             Decimal('3499.00'),
             'Supercharged by M4 Max. Up to 128GB unified memory, 40-core GPU, and the best battery life ever in a Mac.'),
            ('Dell XPS 15', 'dell-xps-15', 'laptops',
             Decimal('1899.99'),
             'InfinityEdge display, 13th Gen Intel Core i9, NVIDIA RTX 4060, precision-crafted from CNC aluminum.'),
            ('Lenovo ThinkPad X1 Carbon', 'lenovo-thinkpad-x1-carbon', 'laptops',
             Decimal('1649.00'),
             'Ultra-lightweight 14" business laptop. Intel Core Ultra, MIL-STD-810H tested, legendary ThinkPad keyboard.'),

            # Headphones
            ('Sony WH-1000XM6', 'sony-wh-1000xm6', 'headphones',
             Decimal('399.99'),
             'Industry-leading noise cancellation with Auto NC Optimizer. 30-hour battery life and premium comfort.'),
            ('AirPods Pro 3', 'airpods-pro-3', 'headphones',
             Decimal('279.00'),
             'Adaptive Audio, Conversation Awareness, and Personalized Spatial Audio. USB-C charging case with speaker.'),
            ('Bose QuietComfort Ultra', 'bose-quietcomfort-ultra', 'headphones',
             Decimal('429.00'),
             'Immersive Spatial Audio meets world-class noise cancellation. CustomTune sound calibration.'),

            # Cameras
            ('Sony Alpha A7 IV', 'sony-alpha-a7-iv', 'cameras',
             Decimal('2498.00'),
             'Full-frame 33MP Exmor R sensor, 4K 60p video, real-time Eye AF, and 10fps continuous shooting.'),
            ('Canon EOS R6 Mark II', 'canon-eos-r6-mark-ii', 'cameras',
             Decimal('2499.00'),
             '24.2MP full-frame CMOS sensor, up to 40fps electronic shutter, 6K RAW video, and subject detection AF.'),

            # Gaming
            ('PlayStation 5 Pro', 'playstation-5-pro', 'gaming',
             Decimal('699.99'),
             'Enhanced GPU, AI-driven upscaling, and 2TB SSD. The most powerful PlayStation ever built.'),
            ('Nintendo Switch 2', 'nintendo-switch-2', 'gaming',
             Decimal('449.99'),
             'Play at home or on-the-go with the next-generation Switch. 8-inch LCD, magnetic Joy-Con controllers.'),
            ('Xbox Series X', 'xbox-series-x', 'gaming',
             Decimal('499.99'),
             '12 teraflops of GPU power, 1TB SSD, 4K gaming at up to 120fps. The fastest, most powerful Xbox ever.'),

            # Accessories
            ('Apple Watch Ultra 3', 'apple-watch-ultra-3', 'accessories',
             Decimal('799.00'),
             'The most rugged Apple Watch. 49mm titanium case, precision dual-frequency GPS, 72-hour battery life.'),
            ('Samsung T9 Portable SSD 2TB', 'samsung-t9-portable-ssd-2tb', 'accessories',
             Decimal('179.99'),
             'Read speeds up to 2,000 MB/s. Shock-resistant rubber exterior. USB 3.2 Gen 2x2.'),
            ('Anker 737 Power Bank 24K', 'anker-737-power-bank-24k', 'accessories',
             Decimal('109.99'),
             '24,000mAh capacity, 140W output, smart digital display. Charge a MacBook Pro to 50% in 30 minutes.'),
        ]

        for name, slug, cat_slug, price, description in products_data:
            product, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'category': categories[cat_slug],
                    'price': price,
                    'description': description,
                    'available': True,
                }
            )
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: Product "{name}" (${price})')

        # Test Coupon
        now = timezone.now()
        coupon, created = Coupon.objects.get_or_create(
            code='ELECTRO15',
            defaults={
                'valid_from': now,
                'valid_to': now + timezone.timedelta(days=365),
                'discount': 15,
                'active': True,
            }
        )
        status = 'Created' if created else 'Exists'
        self.stdout.write(f'  {status}: Coupon "ELECTRO15" (15% off)')

        self.stdout.write(self.style.SUCCESS(
            f'\nDone! {Product.objects.count()} products, '
            f'{Category.objects.count()} categories, '
            f'{Coupon.objects.count()} coupons.'
        ))
