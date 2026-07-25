from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.shortcuts import render
from .models import Coupon
from .forms import CouponApplyForm


@require_POST
def coupon_apply(request):
    """
    Validate and apply a coupon code.

    HTMX behaviour:
      - Returns the cart_summary partial with updated totals,
        swapped into #cart-summary.
      - Sets HX-Trigger to fire a toast notification.

    Non-HTMX fallback:
      - Redirects to the cart detail page.
    """
    now = timezone.now()
    form = CouponApplyForm(request.POST)

    if form.is_valid():
        code = form.cleaned_data['code']
        try:
            coupon = Coupon.objects.get(
                code__iexact=code,
                valid_from__lte=now,
                valid_to__gte=now,
                active=True,
            )
            
            if not coupon.can_be_used():
                request.session['coupon_id'] = None
                if request.headers.get('HX-Request'):
                    from cart.cart import Cart
                    from cart.views import _build_cart_context
                    cart = Cart(request)
                    context = _build_cart_context(request, cart)
                    context['coupon_error'] = 'This coupon has reached its usage limit.'
                    import json
                    response = render(request, 'cart/partials/cart_summary.html', context)
                    response['HX-Trigger'] = json.dumps({
                        'toast': {'message': 'Coupon usage limit reached.', 'type': 'error'}
                    })
                    return response
                return redirect('cart:cart_detail')

            request.session['coupon_id'] = coupon.id

            if request.headers.get('HX-Request'):
                # Build context with cart + coupon info
                from cart.cart import Cart
                from cart.views import _build_cart_context
                cart = Cart(request)
                context = _build_cart_context(request, cart)
                context['coupon_message'] = f'Coupon "{code}" applied!'

                import json
                response = render(
                    request,
                    'cart/partials/cart_summary.html',
                    context,
                )
                
                perk_msg = f'{coupon.discount}% off'
                if coupon.is_free_shipping:
                    perk_msg += ' + Free Shipping'
                    
                response['HX-Trigger'] = json.dumps({
                    'toast': {
                        'message': f'Coupon "{code}" applied — {perk_msg}!',
                        'type': 'success',
                    }
                })
                return response

            return redirect('cart:cart_detail')

        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None

            if request.headers.get('HX-Request'):
                from cart.cart import Cart
                from cart.views import _build_cart_context
                cart = Cart(request)
                context = _build_cart_context(request, cart)
                context['coupon_error'] = 'Invalid or expired coupon code.'

                import json
                response = render(
                    request,
                    'cart/partials/cart_summary.html',
                    context,
                )
                response['HX-Trigger'] = json.dumps({
                    'toast': {
                        'message': 'Invalid or expired coupon code.',
                        'type': 'error',
                    }
                })
                return response

    return redirect('cart:cart_detail')
