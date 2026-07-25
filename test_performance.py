import os
import django
import time
from django.test import Client
from django.db import connection, reset_queries

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
django.setup()

from django.contrib.auth.models import User

def run_performance_tests():
    print("--- INITIATING SYSTEM PERFORMANCE PROFILING ---")
    client = Client(HTTP_HOST='localhost')
    
    # Ensure superuser exists
    user, created = User.objects.get_or_create(username='testadmin', is_staff=True, is_superuser=True)
    if created:
        user.set_password('testpassword')
        user.save()
    else:
        user.set_password('testpassword')
        user.save()

    client.login(username='testadmin', password='testpassword')

    urls_to_test = [
        ('/manage-store/', 'Admin Dashboard'),
        ('/manage-store/shop/product/', 'Product Catalog List'),
        ('/manage-store/orders/order/', 'Order Management List'),
    ]

    report = []
    
    # Enable query logging
    from django.conf import settings
    settings.DEBUG = True

    for url, name in urls_to_test:
        reset_queries()
        start_time = time.time()
        
        response = client.get(url)
        
        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000
        query_count = len(connection.queries)
        
        # Performance analysis
        if elapsed_ms < 200:
            speed_rating = "EXCELLENT"
        elif elapsed_ms < 500:
            speed_rating = "GOOD"
        else:
            speed_rating = "WARNING: SLOW"

        if query_count < 10:
            query_rating = "OPTIMIZED"
        elif query_count < 30:
            query_rating = "ACCEPTABLE"
        else:
            query_rating = "WARNING: N+1 QUERIES LIKELY"

        report.append(f"-> {name} ({url})")
        report.append(f"   Load Time: {elapsed_ms:.2f}ms [{speed_rating}]")
        report.append(f"   Database Queries: {query_count} [{query_rating}]\n")

    print("\n--- PERFORMANCE PROFILING RESULTS ---")
    for line in report:
        print(line)

if __name__ == '__main__':
    run_performance_tests()
