from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from orders.models import Order
from .models import CustomerProfile

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        CustomerProfile.objects.create(user=instance)

@receiver(post_save, sender=Order)
def update_customer_ltv(sender, instance, created, **kwargs):
    if instance.user and instance.status == 'delivered':
        profile, _ = CustomerProfile.objects.get_or_create(user=instance.user)
        
        # Recalculate LTV from all delivered orders
        total_orders = instance.user.orders.filter(status='delivered').count()
        total_ltv = sum(order.get_total_cost() for order in instance.user.orders.filter(status='delivered'))
        
        profile.total_orders = total_orders
        profile.lifetime_value = total_ltv
        profile.last_order_date = instance.created
        
        # VIP threshold logic
        if total_ltv >= 5000:
            profile.is_vip = True
            
        profile.save()
