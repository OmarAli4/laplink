from decimal import Decimal
from urllib.parse import quote
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Order
from .forms import OrderCreateForm, EGYPT_GOVERNORATES
from cart.cart import Cart

FLAT_SHIPPING_COST = Decimal('120.00')
STORE_INSTAPAY_NUMBER = '01009019079'
STORE_WHATSAPP_INTL = '201009019079'


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


def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST, request.FILES)
        express_product_id = request.POST.get('express_product_id')
        if form.is_valid():
            order = form.save(commit=False)
            order.shipping_cost = FLAT_SHIPPING_COST

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
                    product = get_object_or_404(Product, id=express_product_id)

                    class FakeCart(list):
                        def clear(self):
                            pass
                    fake_cart = FakeCart([{'product': product, 'price': product.current_price, 'quantity': 1}])
                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=fake_cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=coupon
                    )
                else:
                    if len(cart) == 0:
                        messages.error(request, 'Your cart is empty.')
                        return redirect('cart:cart_detail')

                    CheckoutFacade.process_checkout(
                        order=order,
                        cart=cart,
                        user=request.user if request.user.is_authenticated else None,
                        coupon=coupon
                    )
            except InsufficientStockError as e:
                messages.error(request, str(e))
                return redirect('cart:cart_detail')

            # Clear coupon from session
            request.session['coupon_id'] = None

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

    from cart.views import _build_cart_context
    context = _build_cart_context(request, cart)
    context['order_form'] = form
    context['governorates'] = EGYPT_GOVERNORATES[1:]  # skip empty placeholder
    context['shipping_cost'] = FLAT_SHIPPING_COST
    context['grand_total'] = context['total_after_discount'] + FLAT_SHIPPING_COST
    context['instapay_number'] = STORE_INSTAPAY_NUMBER

    return render(request, 'orders/order/create.html', context)


def order_track(request, order_id):
    """Display interactive live tracking timeline for an order."""
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)

    step = 1
    if order.status == 'processing':
        step = 2
    elif order.status == 'shipped':
        step = 3
    elif order.status == 'delivered':
        step = 4

    whatsapp_url = _build_whatsapp_order_url(order)
    return render(request, 'orders/order/track.html', {
        'order': order,
        'step': step,
        'whatsapp_url': whatsapp_url,
    })
