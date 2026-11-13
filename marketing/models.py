from decimal import Decimal
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
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
        if not self.is_active or not self.pk:
            return

        products = set(self.specific_products.all())
        for category in self.categories.all():
            products.update(category.products.all())

        discount_multiplier = (Decimal('100') - Decimal(self.discount_percentage)) / Decimal('100')
        for product in products:
            product.sale_price = (product.price * discount_multiplier).quantize(Decimal('0.01'))
            product.sale_start = self.start_time
            product.sale_end = self.end_time
            product.save(update_fields=['sale_price', 'sale_start', 'sale_end'])

    def save(self, *args, **kwargs):
        is_update = self.pk is not None
        super().save(*args, **kwargs)
        if is_update:
            self.apply_to_products()


@receiver(m2m_changed, sender=FlashSale.categories.through)
@receiver(m2m_changed, sender=FlashSale.specific_products.through)
def apply_flash_sale_on_m2m_change(sender, instance, action, **kwargs):
    if action in ('post_add', 'post_remove', 'post_clear'):
        instance.apply_to_products()


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
            existing_codes = set(
                Coupon.objects.filter(code__startswith=f"{self.prefix}-").values_list('code', flat=True)
            )
            coupons_to_create = []
            attempts = 0
            max_attempts = self.quantity * 5 + 20
            while len(coupons_to_create) < self.quantity and attempts < max_attempts:
                attempts += 1
                code = f"{self.prefix}-{get_random_string(length=6).upper()}"
                if code in existing_codes:
                    continue
                existing_codes.add(code)
                coupons_to_create.append(Coupon(
                    code=code,
                    valid_from=self.valid_from,
                    valid_to=self.valid_to,
                    discount=self.discount_percentage,
                    active=True
                ))
            Coupon.objects.bulk_create(coupons_to_create, ignore_conflicts=True)
            self.generated = True
            self.save(update_fields=['generated'])
