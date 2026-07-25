from .models import OrderItem
from shop.services import InventoryService
from emails.services import NotificationService
from django.db import transaction


class InsufficientStockError(Exception):
    """Raised when a product has insufficient stock at checkout time."""
    pass


class CheckoutFacade:
    """
    Facade orchestrating the checkout process and decoupling the view
    from the various subsystems.
    """
    
    @staticmethod
    def process_checkout(order, cart, user=None, coupon=None):
        with transaction.atomic():
            # 1. Attach user and coupon, save order
            if user and user.is_authenticated:
                order.user = user
                
            if coupon:
                order.coupon = coupon
                order.discount = coupon.discount
                order.discount_type = coupon.discount_type
                
            order.save()
            
            # 2. Iterate cart, validate stock, and create order items
            from shop.models import Product
            for item in cart:
                # Lock the product row to prevent concurrent modifications
                product = Product.objects.select_for_update().get(id=item['product'].id)
                
                if product.stock_quantity < item['quantity']:
                    raise InsufficientStockError(
                        f'Insufficient stock for "{product.name}". '
                        f'Only {product.stock_quantity} left.'
                    )
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    price=item['price'],
                    quantity=item['quantity'],
                )
                # 3. Securely deduct stock via InventoryService
                InventoryService.deduct_stock(product, item['quantity'])
            
        # 4. Clear the cart (outside transaction — order is committed)
        cart.clear()
        
        # 5. Send Order Confirmation Email
        NotificationService.send_order_confirmation(order)
        
        # 6. Log User Activity
        if user and user.is_authenticated:
            from actions.utils import create_action
            create_action(user, 'placed an order for', order)

