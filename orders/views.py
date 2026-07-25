from django.shortcuts import render, redirect
from .models import OrderItem
from .forms import OrderCreateForm
from cart.cart import Cart


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        express_product_id = request.POST.get('express_product_id')
        if form.is_valid():
            order = form.save(commit=False)
            coupon = None
            coupon_id = request.session.get('coupon_id')
            if coupon_id:
                from coupons.models import Coupon
                try:
                    coupon = Coupon.objects.get(id=coupon_id)
                except Coupon.DoesNotExist:
                    pass
            
            from .services import CheckoutFacade, InsufficientStockError
            try:
                if express_product_id:
                    from shop.models import Product
                    from django.shortcuts import get_object_or_404
                    product = get_object_or_404(Product, id=express_product_id)
                    class FakeCart(list):
                        def clear(self): pass
                    fake_cart = FakeCart([{'product': product, 'price': product.current_price, 'quantity': 1}])
                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=fake_cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=coupon
                    )
                else:
                    if len(cart) == 0:
                        from django.contrib import messages
                        messages.error(request, 'Your cart is empty.')
                        return redirect('cart:cart_detail')
                        
                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=coupon
                    )
            except InsufficientStockError as e:
                from django.contrib import messages
                messages.error(request, str(e))
                return redirect('cart:cart_detail')
            
            # Clear coupon from session
            request.session['coupon_id'] = None

            return render(request, 'orders/order/created.html', {'order': order})
    else:
        form = OrderCreateForm()

    from cart.views import _build_cart_context
    context = _build_cart_context(request, cart)
    context['order_form'] = form

    return render(request, 'orders/order/create.html', context)


def order_track(request, order_id):
    """Display interactive live tracking timeline for an order."""
    from django.shortcuts import get_object_or_404
    from .models import Order
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    
    step = 1
    if order.status == 'processing':
        step = 2
    elif order.status == 'shipped':
        step = 3
    elif order.status == 'delivered':
        step = 4
        
    return render(request, 'orders/order/track.html', {'order': order, 'step': step})

