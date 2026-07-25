from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order, ReturnRequest
from shop.models import Product
from .models import InventoryLog, PurchaseOrder

@receiver(post_save, sender=Order)
def log_order_inventory(sender, instance, created, **kwargs):
    # For a real app, this should only happen once per order (e.g. when paid).
    # Since we're tracking state via status, we'll check if it just became processing.
    if instance.status == 'processing' and not getattr(instance, '_inventory_deducted', False):
        for item in instance.items.all():
            # Deduct stock
            product = item.product
            product.stock_quantity = max(0, product.stock_quantity - item.quantity)
            product.save(update_fields=['stock_quantity'])
            
            # Log it
            InventoryLog.objects.create(
                product=product,
                quantity_change=-item.quantity,
                reason='sale',
                user=instance.user,
                note=f"Order #{instance.id}"
            )
        # Prevent re-deduction on subsequent saves in the same memory instance
        instance._inventory_deducted = True

@receiver(post_save, sender=ReturnRequest)
def process_return_inventory(sender, instance, created, **kwargs):
    if instance.status == 'approved' and not getattr(instance, '_inventory_restocked', False):
        # Add stock for all items in the returned order
        for item in instance.order.items.all():
            product = item.product
            product.stock_quantity += item.quantity
            product.save(update_fields=['stock_quantity'])

            InventoryLog.objects.create(
                product=product,
                quantity_change=item.quantity,
                reason='return',
                user=instance.user,
                note=f"Return #{instance.id}"
            )
        instance._inventory_restocked = True

@receiver(post_save, sender=Product)
def check_low_stock(sender, instance, created, **kwargs):
    # Auto-draft PO if stock < 10 and no pending PO exists
    LOW_STOCK_THRESHOLD = 10
    if instance.stock_quantity < LOW_STOCK_THRESHOLD:
        po_exists = PurchaseOrder.objects.filter(
            product=instance,
            status__in=['draft', 'sent']
        ).exists()
        if not po_exists:
            PurchaseOrder.objects.create(
                product=instance,
                requested_quantity=50,
                status='draft'
            )
