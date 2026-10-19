from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from shop.models import Category, Product
from orders.models import Order, OrderItem


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
            'email': '',
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

    def test_order_admin_changelist_and_change_view_render(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@laplink.eg',
            password='password123',
        )
        self.client.force_login(admin_user)

        cod_order = Order.objects.create(
            first_name='Ali',
            last_name='Hassan',
            phone='01009019079',
            city='القاهرة - Cairo',
            address='Nasr City',
            payment_method='cod',
            shipping_cost=Decimal('120.00'),
        )
        OrderItem.objects.create(order=cod_order, product=self.product, price=self.product.price, quantity=1)

        instapay_order = Order.objects.create(
            first_name='Sara',
            last_name='Kamel',
            phone='01012345678',
            city='الجيزة - Giza',
            address='Dokki',
            payment_method='instapay',
            instapay_reference='sara@instapay',
            payment_proof='orders/payment_proofs/missing_receipt.webp',
            shipping_cost=Decimal('120.00'),
        )
        OrderItem.objects.create(order=instapay_order, product=self.product, price=self.product.price, quantity=1)

        # 1. Test Order Admin Changelist
        changelist_url = reverse('admin:orders_order_changelist')
        resp_list = self.client.get(changelist_url)
        self.assertEqual(resp_list.status_code, 200)
        self.assertContains(resp_list, 'InstaPay')
        self.assertContains(resp_list, 'COD')

        # 2. Test Order Admin Detail / Change View
        change_url = reverse('admin:orders_order_change', args=[instapay_order.id])
        resp_change = self.client.get(change_url)
        self.assertEqual(resp_change.status_code, 200)

        # 3. Test Admin Action mark_as_paid
        resp_action = self.client.post(changelist_url, {
            'action': 'mark_as_paid',
            '_selected_action': [str(instapay_order.id)],
        })
        self.assertEqual(resp_action.status_code, 302)
        instapay_order.refresh_from_db()
        self.assertTrue(instapay_order.paid)
        self.assertEqual(instapay_order.status, 'processing')

        # 4. Test re-saving order with missing file on disk does not raise FileNotFoundError
        instapay_order.status = 'shipped'
        instapay_order.save()
        self.assertEqual(instapay_order.status, 'shipped')
