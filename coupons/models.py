from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from .strategies import get_discount_strategy


class Coupon(models.Model):
    DISCOUNT_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )

    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True, help_text="Internal campaign note (e.g. 'Black Friday')")
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES, default='percentage')
    discount = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text='Percentage value (0 to 100) or Fixed Amount.',
    )
    is_free_shipping = models.BooleanField(default=False, help_text='Waive all shipping fees if applied.')
    usage_limit = models.PositiveIntegerField(default=0, help_text='Max times this coupon can be used. 0 means unlimited.')
    times_used = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def can_be_used(self):
        """Check if coupon is active and hasn't reached its usage limit."""
        if not self.active:
            return False
        if self.usage_limit > 0 and self.times_used >= self.usage_limit:
            return False
        return True

    def get_discount_amount(self, total: Decimal) -> Decimal:
        """Dynamically calculates discount using the assigned Strategy."""
        strategy = get_discount_strategy(self.discount_type)
        return strategy.calculate_discount(total, Decimal(self.discount))
