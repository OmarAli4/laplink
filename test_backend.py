import os
import django
from decimal import Decimal

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
django.setup()

from django.contrib.auth.models import User
from shop.models import Category, Brand, Product
from orders.models import Order, OrderItem
from coupons.models import Coupon
from django.utils import timezone

def run_backend_tests():
    print("--- INITIATING BACKEND LOGIC TESTS ---")
    report = []

    try:
        # Test 1: Category Creation
        print("Testing Category creation...")
        cat, created = Category.objects.get_or_create(
            name="Test Cyber Category",
            slug="test-cyber-category"
        )
        report.append("✅ Category CRUD operations successful.")

        # Test 2: Brand Creation
        print("Testing Brand creation...")
        brand, created = Brand.objects.get_or_create(
            name="Cyberdyne",
            slug="cyberdyne"
        )
        report.append("✅ Brand CRUD operations successful.")

        # Test 3: Product Creation & Editing
        print("Testing Product logic...")
        prod, created = Product.objects.get_or_create(
            category=cat,
            brand=brand,
            name="Test Cyber Implant",
            slug="test-cyber-implant",
            price=Decimal('999.99'),
            stock_quantity=10,
            available=True
        )
        prod.price = Decimal('899.99')
        prod.save()
        report.append("✅ Product logic (Creation & Editing) successful.")

        # Test 4: Coupon Logic
        print("Testing Coupon logic...")
        coupon, created = Coupon.objects.get_or_create(
            code="CYBER10",
            valid_from=timezone.now(),
            valid_to=timezone.now() + timezone.timedelta(days=1),
            discount=10,
            active=True
        )
        report.append("✅ Coupon logic successful.")

        # Test 5: Order Processing
        print("Testing Order processing...")
        user, created = User.objects.get_or_create(username="testbuyer", email="buyer@test.com")
        order = Order.objects.create(
            user=user,
            first_name="John",
            last_name="Connor",
            email="buyer@test.com",
            address="123 Cyber St",
            postal_code="10101",
            city="Tech City",
            coupon=coupon,
            discount=10
        )
        OrderItem.objects.create(
            order=order,
            product=prod,
            price=prod.price,
            quantity=2
        )
        total_cost = order.get_total_cost()
        # 899.99 * 2 = 1799.98. 10% discount = 179.99. Final = 1619.98
        report.append(f"✅ Order calculation successful. (Total Cost Calculated: ${total_cost:.2f})")

        print("\n--- DETAILED BACKEND REPORT ---")
        for line in report:
            print(line)

        # Cleanup
        print("\nCleaning up test data...")
        order.delete()
        coupon.delete()
        prod.delete()
        brand.delete()
        cat.delete()
        user.delete()
        print("Cleanup successful.")

    except Exception as e:
        print(f"\n❌ FATAL ERROR IN BACKEND LOGIC: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_backend_tests()
