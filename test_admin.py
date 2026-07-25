import os
import django
from django.test import Client

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
django.setup()

from django.contrib.auth.models import User

def run_tests():
    print("Initializing Admin Functionality Test...")
    client = Client(HTTP_HOST='localhost')
    
    # Ensure superuser exists
    user, created = User.objects.get_or_create(username='testadmin', is_staff=True, is_superuser=True)
    if created:
        user.set_password('testpassword')
        user.save()
    else:
        user.set_password('testpassword')
        user.save()

    print("Logging in as superuser...")
    login_success = client.login(username='testadmin', password='testpassword')
    if not login_success:
        print("ERROR: Failed to log in.")
        return

    urls_to_test = [
        ('/manage-store/', 'Dashboard'),
        ('/manage-store/shop/product/', 'Product List'),
        ('/manage-store/shop/product/add/', 'Add Product Page'),
        ('/manage-store/orders/order/', 'Order List'),
        ('/manage-store/shop/category/', 'Category List'),
        ('/manage-store/coupons/coupon/', 'Coupon List'),
        ('/manage-store/shop/brand/', 'Brand List'),
        ('/manage-store/auth/user/', 'User List'),
        ('/manage-store/emails/emaillog/', 'Email Logs'),
    ]

    report = []
    
    for url, name in urls_to_test:
        print(f"Testing {name} ({url})...")
        try:
            response = client.get(url)
            if response.status_code == 200:
                report.append(f"[SUCCESS] {name}: OK (200)")
            else:
                report.append(f"[FAILED] {name}: Failed with status {response.status_code}")
        except Exception as e:
            report.append(f"[ERROR] {name}: Crashed with exception: {e}")

    print("\n--- TEST REPORT ---")
    for line in report:
        print(line)
        
    print("\nTest completed.")

if __name__ == '__main__':
    run_tests()
