from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from orders.models import Order, ReturnRequest
from shop.models import Product
from .models import InventoryLog, PurchaseOrder


@receiver(post_save, sender=Order)
def log_order_inventory(sender, instance, created, **kwargs):
    order_sale_note = f"Order #{instance.id}"
    order_cancel_note = f"Cancelled Order #{instance.id}"

    if instance.status == 'processing':
        if not InventoryLog.objects.filter(reason='sale', note=order_sale_note).exists():
            for item in instance.items.select_related('product').all():
                product = item.product
                Product.objects.filter(id=product.id).update(
                    stock_quantity=F('stock_quantity') - item.quantity
                )
                product.refresh_from_db(fields=['stock_quantity'])
                if product.stock_quantity < 0:
                    product.stock_quantity = 0
                    product.save(update_fields=['stock_quantity'])

                InventoryLog.objects.create(
                    product=product,
                    quantity_change=-item.quantity,
                    reason='sale',
                    user=instance.user,
                    note=order_sale_note,
                )
    elif instance.status == 'cancelled':
        if (
            InventoryLog.objects.filter(reason='sale', note=order_sale_note).exists()
            and not InventoryLog.objects.filter(reason='return', note=order_cancel_note).exists()
        ):
            for item in instance.items.select_related('product').all():
                product = item.product
                Product.objects.filter(id=product.id).update(
                    stock_quantity=F('stock_quantity') + item.quantity
                )
                product.refresh_from_db(fields=['stock_quantity'])
                InventoryLog.objects.create(
                    product=product,
                    quantity_change=item.quantity,
                    reason='return',
                    user=instance.user,
                    note=order_cancel_note,
                )


@receiver(post_save, sender=ReturnRequest)
def process_return_inventory(sender, instance, created, **kwargs):
    return_note = f"Return #{instance.id}"
    if instance.status == 'approved' and not InventoryLog.objects.filter(reason='return', note=return_note).exists():
        for item in instance.order.items.select_related('product').all():
            product = item.product
            Product.objects.filter(id=product.id).update(
                stock_quantity=F('stock_quantity') + item.quantity
            )
            product.refresh_from_db(fields=['stock_quantity'])

            InventoryLog.objects.create(
                product=product,
                quantity_change=item.quantity,
                reason='return',
                user=instance.user,
                note=return_note,
            )


@receiver(post_save, sender=Product)
def check_low_stock(sender, instance, created, **kwargs):
    LOW_STOCK_THRESHOLD = 10
    if not isinstance(instance.stock_quantity, int):
        instance.refresh_from_db(fields=['stock_quantity'])
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
