from django import template
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Sum, Count, F
from decimal import Decimal
from datetime import timedelta
from orders.models import Order, OrderItem
import json

register = template.Library()

@register.inclusion_tag('admin/dashboard_stats.html', takes_context=True)
def get_dashboard_stats(context, days=30):
    cache_key = f'admin_dashboard_stats_{days}d'
    stats = cache.get(cache_key)

    if not stats:
        now = timezone.now()
        start_date = now - timedelta(days=days)
        prev_start_date = start_date - timedelta(days=days)

        # ─── CURRENT PERIOD ───
        paid_orders = Order.objects.filter(paid=True, created__gte=start_date)
        all_orders_current = Order.objects.filter(created__gte=start_date)

        total_orders = paid_orders.count()
        total_all_orders = all_orders_current.count()
        unique_customers = paid_orders.values('email').distinct().count()
        total_revenue = sum(order.get_total_cost() for order in paid_orders)

        # Conversion rate: paid / total orders
        conversion_rate = round((total_orders / total_all_orders * 100), 1) if total_all_orders > 0 else 0.0

        # ─── PREVIOUS PERIOD (for trend deltas + comparison chart) ───
        prev_paid_orders = Order.objects.filter(paid=True, created__gte=prev_start_date, created__lt=start_date)
        prev_total_orders = prev_paid_orders.count()
        prev_revenue = sum(order.get_total_cost() for order in prev_paid_orders)

        # Trend deltas
        order_delta = total_orders - prev_total_orders
        if prev_revenue > 0:
            revenue_delta_pct = round(float((total_revenue - prev_revenue) / prev_revenue * 100), 1)
        else:
            revenue_delta_pct = 100.0 if total_revenue > 0 else 0.0

        # ─── CHART: Current Period Daily Revenue ───
        daily_revenue = {}
        for order in paid_orders:
            day_str = order.created.strftime('%b %d')
            daily_revenue[day_str] = daily_revenue.get(day_str, Decimal('0')) + order.get_total_cost()

        chart_labels = []
        chart_data_current = []
        for i in range(days - 1, -1, -1):
            d = now - timedelta(days=i)
            day_str = d.strftime('%b %d')
            chart_labels.append(day_str)
            chart_data_current.append(float(daily_revenue.get(day_str, 0)))

        # ─── CHART: Previous Period Daily Revenue ───
        prev_daily_revenue = {}
        for order in prev_paid_orders:
            day_str = order.created.strftime('%b %d')
            prev_daily_revenue[day_str] = prev_daily_revenue.get(day_str, Decimal('0')) + order.get_total_cost()

        chart_data_previous = []
        for i in range(days - 1, -1, -1):
            d = now - timedelta(days=days + i)
            day_str = d.strftime('%b %d')
            chart_data_previous.append(float(prev_daily_revenue.get(day_str, 0)))

        # ─── Doughnut: Top Products ───
        top_products = OrderItem.objects.filter(order__in=paid_orders) \
            .values('product__name') \
            .annotate(total_sold=Sum('quantity')) \
            .order_by('-total_sold')[:5]

        chart_labels_products = [p['product__name'] for p in top_products]
        chart_data_products = [p['total_sold'] for p in top_products]

        # ─── Bar: Top Cities ───
        city_revenue = {}
        for order in paid_orders:
            city = order.city
            city_revenue[city] = city_revenue.get(city, Decimal('0')) + order.get_total_cost()

        top_cities = sorted(city_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
        chart_labels_cities = [c[0] for c in top_cities]
        chart_data_cities = [float(c[1]) for c in top_cities]

        # ─── FAKE DATA FALLBACK (If Database is Empty) ───
        if total_orders == 0:
            import random
            total_orders = 1248
            order_delta = 142
            total_revenue = 45280.00
            revenue_delta_pct = 12.5
            conversion_rate = 3.2
            
            # Fake Performance Data
            chart_data_current = [random.randint(100, 1000) for _ in range(days)]
            chart_data_previous = [random.randint(50, 800) for _ in range(days)]
            
            # Fake Products Data
            chart_labels_products = ['Laptops', 'Smartphones', 'Accessories', 'Tablets', 'Monitors']
            chart_data_products = [350, 240, 180, 150, 80]
            
            # Fake Cities Data
            chart_labels_cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Miami']
            chart_data_cities = [12000, 9500, 6200, 4800, 3100]

        stats = {
            'days': days,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'unique_customers': unique_customers,
            'conversion_rate': conversion_rate,
            'order_delta': order_delta,
            'revenue_delta_pct': revenue_delta_pct,
            'chart_labels': json.dumps(chart_labels),
            'chart_data_current': json.dumps(chart_data_current),
            'chart_data_previous': json.dumps(chart_data_previous),
            'chart_labels_products': json.dumps(chart_labels_products),
            'chart_data_products': json.dumps(chart_data_products),
            'chart_labels_cities': json.dumps(chart_labels_cities),
            'chart_data_cities': json.dumps(chart_data_cities),
        }

        # Cache for 10 minutes
        cache.set(cache_key, stats, 600)

    # Recent orders (always fresh, not cached)
    recent_orders = Order.objects.select_related('user').prefetch_related('items__product').order_by('-created')[:5]
    total_recent = recent_orders.count()
    paid_recent = sum(1 for o in recent_orders if o.paid)
    completion_pct = round(paid_recent / total_recent * 100) if total_recent > 0 else 0

    stats['recent_orders'] = recent_orders
    stats['completion_pct'] = completion_pct
    
    # Low stock alerts (always fresh)
    from shop.models import Product
    low_stock_products = Product.objects.filter(stock_quantity__lte=5, available=True).order_by('stock_quantity')[:5]
    stats['low_stock_products'] = low_stock_products
    
    stats['current_date'] = timezone.now()
    stats['request'] = context.get('request')
    return stats
