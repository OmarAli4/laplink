from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from shop.models import Product
from .cart import Cart
from .forms import CartAddProductForm


@require_POST
def cart_add(request, product_id):
    """
    Add a product to the cart.

    HTMX behaviour:
      - Returns ONLY the cart_counter partial (swapped into #cart-counter).
      - Also sets HX-Trigger header to fire a 'toast' event for Alpine.js
        notification.

    Non-HTMX fallback:
      - Redirects to the full cart detail page.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        requested_qty = cd['quantity']
        current_qty = cart.cart.get(str(product.id), {}).get('quantity', 0)
        
        if cd['override']:
            new_total = requested_qty
        else:
            new_total = current_qty + requested_qty
            
        if new_total > product.stock_quantity:
            # Send an error toast via HTMX
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse(status=204) # No content, just the header trigger
                import json
                response['HX-Trigger'] = json.dumps({
                    'toast': {
                        'message': f'Cannot add. Only {product.stock_quantity} left in stock.',
                        'type': 'error',
                    }
                })
                return response
            return redirect('cart:cart_detail')
            
        cart.add(
            product=product,
            quantity=requested_qty,
            override_quantity=cd['override'],
        )

    # ── Check for Direct Buy Now Redirect ──
    if request.POST.get('buy_now') == 'true' or request.GET.get('buy_now') == 'true':
        if request.headers.get('HX-Request'):
            from django.http import HttpResponse
            from django.urls import reverse
            response = HttpResponse(status=200)
            response['HX-Redirect'] = reverse('orders:order_create')
            return response
        return redirect('orders:order_create')

    # ── HTMX Request → return partial ──
    if request.headers.get('HX-Request'):
        from django.http import HttpResponse
        response = render(
            request,
            'cart/partials/cart_counter.html',
            {'cart': cart},
        )
        # Trigger Alpine.js toast notification via HTMX response header
        import json
        response['HX-Trigger'] = json.dumps({
            'toast': {
                'message': f'"{product.name}" added to cart!',
                'type': 'success',
            }
        })
        return response

    return redirect('cart:cart_detail')


@require_POST
def cart_update(request, product_id):
    """
    Update the quantity of a product already in the cart.

    HTMX: returns the cart table + summary partials.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        requested_qty = cd['quantity']
        
        if requested_qty > product.stock_quantity:
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse(status=204)
                import json
                response['HX-Trigger'] = json.dumps({
                    'toast': {
                        'message': f'Cannot update. Only {product.stock_quantity} left in stock.',
                        'type': 'error',
                    }
                })
                return response
            return redirect('cart:cart_detail')
            
        cart.add(
            product=product,
            quantity=requested_qty,
            override_quantity=True,
        )

    if request.headers.get('HX-Request'):
        # Recompute coupon discount if one is applied
        context = _build_cart_context(request, cart)
        return render(
            request,
            'cart/partials/cart_content.html',
            context,
        )

    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    """
    Remove a product from the cart entirely.

    HTMX: returns the updated cart table + summary partials.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)

    if request.headers.get('HX-Request'):
        context = _build_cart_context(request, cart)
        return render(
            request,
            'cart/partials/cart_content.html',
            context,
        )

    return redirect('cart:cart_detail')


def cart_detail(request):
    """
    Display the full cart page.
    Always returns the complete template (never a partial).
    """
    cart = Cart(request)
    # Prepare override forms for each item
    for item in cart:
        item['update_quantity_form'] = CartAddProductForm(
            initial={
                'quantity': item['quantity'],
                'override': True,
            }
        )

    context = _build_cart_context(request, cart)
    return render(request, 'cart/detail.html', context)


def _build_cart_context(request, cart):
    """
    Build the shared context dict used by both the full page
    and partial templates. Handles coupon discount calculation.
    """
    from coupons.forms import CouponApplyForm

    coupon_apply_form = CouponApplyForm()
    coupon = None
    discount = 0
    coupon_code = None

    # Check if a coupon is stored in the session
    coupon_id = request.session.get('coupon_id')
    if coupon_id:
        from coupons.models import Coupon
        from django.utils import timezone
        try:
            coupon = Coupon.objects.get(
                id=coupon_id,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
                active=True,
            )
            discount = coupon.discount
            coupon_code = coupon.code
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

    total_before_discount = cart.get_total_price()

    if coupon:
        discount_amount = coupon.get_discount_amount(total_before_discount)
        total_after_discount = total_before_discount - discount_amount
    else:
        discount_amount = 0
        total_after_discount = total_before_discount

    # Re-attach update forms for iteration in partials
    for item in cart:
        if 'update_quantity_form' not in item:
            item['update_quantity_form'] = CartAddProductForm(
                initial={
                    'quantity': item['quantity'],
                    'override': True,
                }
            )

    return {
        'cart': cart,
        'coupon_apply_form': coupon_apply_form,
        'coupon': coupon,
        'coupon_code': coupon_code,
        'discount': discount,
        'discount_amount': discount_amount,
        'total_before_discount': total_before_discount,
        'total_after_discount': total_after_discount,
    }
