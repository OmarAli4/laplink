from decimal import Decimal
from django.conf import settings
from shop.models import Product


class Cart:
    """
    Session-based shopping cart.
    """

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # Save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    MAX_CART_ITEMS = 50  # Prevent session storage abuse

    def add(self, product, quantity=1, override_quantity=False):
        """Add a product to the cart or update its quantity."""
        product_id = str(product.id)
        if product_id not in self.cart:
            if len(self.cart) >= self.MAX_CART_ITEMS:
                return False  # Cart is full
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.current_price),
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()
        return True

    def save(self):
        """Mark the session as modified to ensure it gets saved."""
        self.session.modified = True

    def remove(self, product):
        """Remove a product from the cart."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def _sync_live_products(self):
        """
        Sync session cart items with live DB products and current prices,
        removing products that were deleted or deactivated.
        Returns {product_id_str: Product}.
        """
        product_ids = [pid for pid in self.cart.keys() if str(pid).isdigit()]
        products = Product.objects.filter(
            id__in=product_ids,
            available=True,
        ).select_related('category', 'brand')
        product_map = {str(p.id): p for p in products}

        modified = False
        for pid in list(self.cart.keys()):
            if pid not in product_map:
                del self.cart[pid]
                modified = True
            else:
                live_price = str(product_map[pid].current_price)
                if self.cart[pid].get('price') != live_price:
                    self.cart[pid]['price'] = live_price
                    modified = True

        if modified:
            self.save()

        return product_map

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        import copy
        product_map = self._sync_live_products()
        cart = copy.deepcopy(self.cart)

        for pid, item in cart.items():
            product = product_map.get(pid)
            if not product:
                continue
            item['product'] = product
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """Count all items in the cart."""
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        self._sync_live_products()
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )

    def clear(self):
        """Remove cart from session."""
        del self.session[settings.CART_SESSION_ID]
        self.save()
