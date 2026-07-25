from django import template
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta, datetime
from shop.models import Product, Category
from orders.models import Order
from django.contrib.auth import get_user_model
import json

User = get_user_model()
register = template.Library()

@register.inclusion_tag('admin/includes/dashboard_stats.html')
def render_dashboard_stats():
    # Revenue (Paid orders only)
    paid_orders = Order.objects.filter(paid=True)
    total_revenue = sum(order.get_total_cost() for order in paid_orders)

    # Orders (Completed/Paid)
    total_orders = paid_orders.count()
    
    # Low stock products (less than 10 units)
    low_stock = Product.objects.filter(stock_quantity__lt=10, available=True).order_by('stock_quantity')[:5]
    
    # Recent paid orders
    recent_orders = Order.objects.filter(paid=True).order_by('-created')[:5]
    
    # Active Users
    total_users = User.objects.filter(is_active=True).count()
    
    # Total Products
    total_products = Product.objects.filter(available=True).count()
    
    # 7-Day Chart Data Calculation
    today = timezone.now().date()
    dates = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    chart_labels = [d.strftime('%a') for d in dates]
    
    chart_revenue = []
    chart_order_counts = []
    
    for d in dates:
        day_orders = paid_orders.filter(created__date=d)
        rev = sum(o.get_total_cost() for o in day_orders)
        chart_revenue.append(float(rev))
        chart_order_counts.append(day_orders.count())
        
    # Top Categories with product count
    categories = Category.objects.annotate(num_products=Count('products')).order_by('-num_products')[:4]
    
    return {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': total_products,
        'low_stock_products': low_stock,
        'recent_orders': recent_orders,
        'total_users': total_users,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_revenue_json': json.dumps(chart_revenue),
        'chart_orders_json': json.dumps(chart_order_counts),
        'categories': categories,
    }
