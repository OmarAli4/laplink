from django.db import models
from django.conf import settings
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from shop.models import Product
from coupons.models import Coupon


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Payment'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    DISCOUNT_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid = models.BooleanField(default=False)
    coupon = models.ForeignKey(
        Coupon, related_name='orders',
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES, default='percentage')
    discount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    tracking_number = models.CharField(max_length=100, blank=True)
    shipping_provider = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['user', '-created']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        from coupons.strategies import get_discount_strategy
        total = sum((item.get_cost() for item in self.items.all()), Decimal('0'))
        strategy = get_discount_strategy(self.discount_type)
        return total - strategy.calculate_discount(total, Decimal(self.discount))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class ReturnRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    )

    order = models.ForeignKey(Order, related_name='returns', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='returns', on_delete=models.CASCADE)
    reason = models.TextField(help_text="Customer reason for return")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"Return #{self.id} for Order #{self.order.id}"
