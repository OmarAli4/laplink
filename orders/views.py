from decimal import Decimal
import re
from urllib.parse import quote
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext as _
from .models import Order
from .forms import OrderCreateForm, EGYPT_GOVERNORATES
from cart.cart import Cart

FLAT_SHIPPING_COST = Decimal('120.00')
FREE_SHIPPING_THRESHOLD = Decimal('5000.00')
STORE_INSTAPAY_NUMBER = '01009019079'
STORE_WHATSAPP_INTL = '201009019079'


def _calculate_shipping_cost(subtotal_after_discount, coupon=None, has_items=True):
    if coupon and getattr(coupon, 'is_free_shipping', False):
        return Decimal('0.00')
    if has_items and subtotal_after_discount >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return FLAT_SHIPPING_COST


def _build_whatsapp_order_url(order):
    """Generates a pre-filled WhatsApp confirmation URL for 01009019079."""
    payment_label = "انستا باي (InstaPay)" if order.payment_method == 'instapay' else "الدفع عند الاستلام (COD)"
    items_lines = []
    for item in order.items.all():
        items_lines.append(f"• {item.quantity}x {item.product.name} ({item.get_cost()} ج.م)")
    items_text = "\n".join(items_lines)

    msg = (
        f"أهلاً Lap Link 👋\n"
        f"أرغب في تأكيد طلبي رقم #{order.id}\n\n"
        f"👤 الاسم: {order.full_name}\n"
        f"📱 الموبايل: {order.phone}\n"
        f"📍 المحافظة: {order.city}\n"
        f"🏠 العنوان: {order.address}\n"
        f"💳 طريقة الدفع: {payment_label}\n"
    )
    if order.payment_method == 'instapay':
        if order.instapay_reference:
            msg += f"🔖 مرجع انستا باي: {order.instapay_reference}\n"
        msg += "📸 (مرفق إيصال تحويل InstaPay)\n"

    msg += (
        f"\n📦 المنتجات:\n{items_text}\n"
        f"🚚 الشحن: {order.shipping_cost} ج.م\n"
        f"💰 الإجمالي النهائي: {order.get_total_cost()} ج.م"
    )
    return f"https://wa.me/{STORE_WHATSAPP_INTL}?text={quote(msg)}"


def _remember_order_in_session(request, order_id):
    recent = list(request.session.get('recent_order_ids', []))
    if order_id not in recent:
        recent.append(order_id)
    request.session['recent_order_ids'] = recent[-20:]
    request.session.modified = True


def _get_valid_session_coupon(request):
    coupon_id = request.session.get('coupon_id')
    if not coupon_id:
        return None
    from coupons.models import Coupon
    now = timezone.now()
    try:
        coupon = Coupon.objects.get(
            id=coupon_id,
            valid_from__lte=now,
            valid_to__gte=now,
            active=True,
        )
        if coupon.can_be_used():
            return coupon
    except Coupon.DoesNotExist:
        pass
    request.session['coupon_id'] = None
    return None


def order_create(request):
    cart = Cart(request)
    express_product = None
    express_product_id = (
        request.POST.get('express_product_id')
        or request.GET.get('express_product_id')
        or ''
    ).strip()
    if express_product_id and express_product_id.isdigit():
        from shop.models import Product
        express_product = Product.objects.filter(id=int(express_product_id), available=True).first()

    if request.method == 'POST':
        form = OrderCreateForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)

            from .services import CheckoutFacade, InsufficientStockError
            try:
                if express_product_id:
                    if not express_product:
                        from shop.models import Product
                        express_product = get_object_or_404(Product, id=express_product_id, available=True)

                    class FakeCart(list):
                        def clear(self):
                            pass

                    subtotal = express_product.current_price
                    order.shipping_cost = _calculate_shipping_cost(subtotal, coupon=None, has_items=True)
                    fake_cart = FakeCart([{'product': express_product, 'price': express_product.current_price, 'quantity': 1}])
                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=fake_cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=None,
                    )
                else:
                    if len(cart) == 0:
                        messages.error(request, _('Your cart is empty.'))
                        return redirect('cart:cart_detail')

                    coupon = _get_valid_session_coupon(request)
                    total_before = cart.get_total_price()
                    discount_amt = coupon.get_discount_amount(total_before) if coupon else Decimal('0.00')
                    subtotal_after = total_before - discount_amt
                    order.shipping_cost = _calculate_shipping_cost(subtotal_after, coupon=coupon, has_items=True)

                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=coupon,
                    )
                    request.session['coupon_id'] = None
            except InsufficientStockError as e:
                messages.error(request, str(e))
                if not express_product_id:
                    return redirect('cart:cart_detail')
                form.add_error(None, str(e))
            else:
                _remember_order_in_session(request, order.id)
                whatsapp_url = _build_whatsapp_order_url(order)
                return render(request, 'orders/order/created.html', {
                    'order': order,
                    'whatsapp_url': whatsapp_url,
                    'instapay_number': STORE_INSTAPAY_NUMBER,
                })
    else:
        initial = {'payment_method': 'cod'}
        if request.user.is_authenticated:
            full_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            initial['first_name'] = full_name
            initial['email'] = request.user.email
        form = OrderCreateForm(initial=initial)

    if express_product:
        express_price = express_product.current_price
        shipping_cost = _calculate_shipping_cost(express_price, coupon=None, has_items=True)
        context = {
            'cart': [{'product': express_product, 'price': express_price, 'quantity': 1, 'total_price': express_price}],
            'coupon': None,
            'coupon_code': None,
            'discount': 0,
            'discount_amount': Decimal('0.00'),
            'total_before_discount': express_price,
            'total_after_discount': express_price,
            'express_product': express_product,
        }
    else:
        from cart.views import _build_cart_context
        context = _build_cart_context(request, cart)
        shipping_cost = _calculate_shipping_cost(
            context['total_after_discount'],
            coupon=context.get('coupon'),
            has_items=len(cart) > 0,
        )

    context['order_form'] = form
    context['governorates'] = EGYPT_GOVERNORATES[1:]  # skip empty placeholder
    context['shipping_cost'] = shipping_cost
    context['grand_total'] = context['total_after_discount'] + shipping_cost
    context['instapay_number'] = STORE_INSTAPAY_NUMBER

    return render(request, 'orders/order/create.html', context)


def order_track(request, order_id):
    """Display interactive live tracking timeline for an order (with ownership/phone verification)."""
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)

    is_authorized = (
        request.user.is_staff
        or request.user.is_superuser
        or (request.user.is_authenticated and order.user_id == request.user.id)
        or (order.id in request.session.get('recent_order_ids', []))
    )

    phone_query = (request.POST.get('phone') or request.GET.get('phone') or '').strip()
    phone_error = False
    if not is_authorized and phone_query:
        query_digits = re.sub(r'\D', '', phone_query)
        order_digits = re.sub(r'\D', '', order.phone or '')
        if len(query_digits) >= 4 and len(order_digits) >= 4 and order_digits.endswith(query_digits[-4:]):
            is_authorized = True
            _remember_order_in_session(request, order.id)
        else:
            phone_error = True

    if not is_authorized:
        return render(request, 'orders/order/track.html', {
            'order_locked': True,
            'order_id': order_id,
            'phone_error': phone_error,
        })

    step = 1
    if order.status == 'processing':
        step = 2
    elif order.status == 'shipped':
        step = 3
    elif order.status == 'delivered':
        step = 4

    whatsapp_url = _build_whatsapp_order_url(order)
    return render(request, 'orders/order/track.html', {
        'order_locked': False,
        'order': order,
        'order_id': order.id,
        'step': step,
        'whatsapp_url': whatsapp_url,
    })
