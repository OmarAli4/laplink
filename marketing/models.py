from django.db import models
from shop.models import Product, Category
from coupons.models import Coupon
from django.utils.crypto import get_random_string

class FlashSale(models.Model):
    name = models.CharField(max_length=200, help_text="e.g. Black Friday Cyber Sale")
    discount_percentage = models.PositiveIntegerField(help_text="e.g. 15 for 15% off")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    categories = models.ManyToManyField(Category, blank=True, related_name='flash_sales')
    specific_products = models.ManyToManyField(Product, blank=True, related_name='flash_sales')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.discount_percentage}%)"

    def apply_to_products(self):
        """Applies the discount to all linked products via their native sale fields."""
        if not self.is_active:
            return
            
        products = set(self.specific_products.all())
        for category in self.categories.all():
            products.update(category.products.all())

        for product in products:
            discount_multiplier = 1 - (self.discount_percentage / 100.0)
            product.sale_price = float(product.price) * discount_multiplier
            product.sale_start = self.start_time
            product.sale_end = self.end_time
            product.save(update_fields=['sale_price', 'sale_start', 'sale_end'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.apply_to_products()

class CouponBatch(models.Model):
    name = models.CharField(max_length=100, help_text="e.g. Summer Influencer Batch")
    prefix = models.CharField(max_length=10, help_text="e.g. SUM for SUM-XXXXX")
    quantity = models.PositiveIntegerField(default=100, help_text="How many codes to generate")
    discount_percentage = models.PositiveIntegerField(default=10)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    generated = models.BooleanField(default=False)

    def __str__(self):
        return f"Batch: {self.name} ({self.quantity} codes)"

    def generate_codes(self):
        if not self.generated:
            for _ in range(self.quantity):
                code = f"{self.prefix}-{get_random_string(length=6).upper()}"
                Coupon.objects.create(
                    code=code,
                    valid_from=self.valid_from,
                    valid_to=self.valid_to,
                    discount=self.discount_percentage,
                    active=True
                )
            self.generated = True
            self.save(update_fields=['generated'])
