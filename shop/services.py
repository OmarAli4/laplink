from django.db.models import F

class InventoryService:
    """
    Handles inventory and stock-related business logic.
    """
    
    @staticmethod
    def deduct_stock(product, quantity):
        """
        Securely deducts stock using DB-level F expressions to prevent race conditions.
        """
        product.stock_quantity = F('stock_quantity') - quantity
        product.save(update_fields=['stock_quantity'])
