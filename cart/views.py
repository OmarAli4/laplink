from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
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
                        'message': _('Cannot add. Only %(count)s left in stock.') % {'count': product.stock_quantity},
                        'type': 'error',
                    }
                })
                return response
            return redirect('cart:cart_detail')

        added = cart.add(
            product=product,
            quantity=requested_qty,
            override_quantity=cd['override'],
        )
        if not added:
            if request.headers.get('HX-Request'):
                from django.http import HttpResponse
                response = HttpResponse(status=204)
                import json
                response['HX-Trigger'] = json.dumps({
                    'toast': {
                        'message': _('Maximum cart limit (50 items) reached.'),
                        'type': 'error',
                    }
                })
                return response
            return redirect('cart:cart_detail')

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
        response = render(
            request,
            'cart/partials/cart_counter.html',
            {'cart': cart},
        )
        # Trigger Alpine.js toast notification via HTMX response header
        import json
        response['HX-Trigger'] = json.dumps({
            'toast': {
                'message': _('"%(name)s" added to cart!') % {'name': product.name},
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
                        'message': _('Cannot update. Only %(count)s left in stock.') % {'count': product.stock_quantity},
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
    from coupons.models import Coupon
    from django.utils import timezone

    now = timezone.now()
    coupon_apply_form = CouponApplyForm()
    coupon = None
    discount = 0
    coupon_code = None

    # Check if a coupon is stored in the session
    coupon_id = request.session.get('coupon_id')
    if coupon_id:
        try:
            candidate = Coupon.objects.get(
                id=coupon_id,
                valid_from__lte=now,
                valid_to__gte=now,
                active=True,
            )
            if candidate.can_be_used():
                coupon = candidate
                discount = coupon.discount
                coupon_code = coupon.code
            else:
                request.session['coupon_id'] = None
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

    active_coupons = [
        c for c in Coupon.objects.filter(
            active=True,
            valid_from__lte=now,
            valid_to__gte=now,
        )[:6]
        if c.can_be_used()
    ]

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
        'active_coupons': active_coupons,
    }
