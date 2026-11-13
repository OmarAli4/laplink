from django.db.models import F


class InventoryService:
    """
    Handles inventory and stock-related business logic.
    """

    @staticmethod
    def deduct_stock(product, quantity):
        """
        Securely deducts stock using atomic DB-level F expressions and refreshes the instance.
        """
        ProductModel = type(product)
        updated = ProductModel.objects.filter(
            id=product.id,
            stock_quantity__gte=quantity,
        ).update(stock_quantity=F('stock_quantity') - quantity)
        product.refresh_from_db(fields=['stock_quantity'])
        if not updated:
            from orders.services import InsufficientStockError
            raise InsufficientStockError(
                f'Insufficient stock for "{product.name}". '
                f'Only {product.stock_quantity} left.'
            )
        from inventory.signals import check_low_stock
        check_low_stock(sender=ProductModel, instance=product, created=False)
