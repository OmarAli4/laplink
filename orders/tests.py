from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from shop.models import Category, Product
from orders.models import Order


class CheckoutAndInstaPayTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Chargers', slug='chargers')
        self.product = Product.objects.create(
            category=self.category,
            name='Anker 100W GaN Charger',
            slug='anker-100w-gan-charger',
            price=Decimal('1500.00'),
            stock_quantity=10,
            available=True,
        )

    def test_checkout_page_renders_with_shipping_and_instapay(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 1, 'override': False})
        resp = self.client.get(reverse('orders:order_create'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '01009019079')
        self.assertContains(resp, '120')
        self.assertContains(resp, '1620')

    def test_cod_checkout_adds_120_shipping_and_optional_email(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 1, 'override': False})
        resp = self.client.post(reverse('orders:order_create'), {
            'first_name': 'أحمد محمد علي',
            'phone': '01009019079',
            'email': '',  # Optional email
            'city': 'القاهرة - Cairo',
            'address': 'مدينة نصر، شارع عباس العقاد',
            'payment_method': 'cod',
        })
        self.assertEqual(resp.status_code, 200)
        order = Order.objects.first()
        self.assertIsNotNone(order)
        self.assertEqual(order.first_name, 'أحمد')
        self.assertEqual(order.last_name, 'محمد علي')
        self.assertEqual(order.payment_method, 'cod')
        self.assertEqual(order.shipping_cost, Decimal('120.00'))
        self.assertEqual(order.get_total_cost(), Decimal('1620.00'))
        self.assertContains(resp, 'https://wa.me/201009019079')

    def test_instapay_checkout_stores_reference(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 2, 'override': False})
        resp = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Omar Ali',
            'phone': '+20 100 901 9079',
            'city': 'الجيزة - Giza',
            'address': 'الدقي، شارع التحرير',
            'payment_method': 'instapay',
            'instapay_reference': 'omar@instapay',
        })
        self.assertEqual(resp.status_code, 200)
        order = Order.objects.first()
        self.assertEqual(order.phone, '01009019079')
        self.assertEqual(order.payment_method, 'instapay')
        self.assertEqual(order.instapay_reference, 'omar@instapay')
        # 2 * 1500 + 120 shipping = 3120.00
        self.assertEqual(order.get_total_cost(), Decimal('3120.00'))

    def test_invalid_phone_rejected(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 1, 'override': False})
        resp = self.client.post(reverse('orders:order_create'), {
            'first_name': 'Test User',
            'phone': '12345',
            'city': 'القاهرة - Cairo',
            'address': 'Test Address',
            'payment_method': 'cod',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
