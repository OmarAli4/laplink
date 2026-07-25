from django.db import models
from django.conf import settings
from shop.models import Product

class InventoryLog(models.Model):
    REASON_CHOICES = (
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('manual', 'Manual Adjustment'),
        ('restock', 'Supplier Restock'),
    )

    product = models.ForeignKey(Product, related_name='inventory_logs', on_delete=models.CASCADE)
    quantity_change = models.IntegerField(help_text="Positive for addition, negative for deduction")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, help_text="User who made the change (or None if automated)")
    timestamp = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.product.name} ({self.quantity_change}) - {self.reason}"

class PurchaseOrder(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent to Supplier'),
        ('received', 'Received & Restocked'),
        ('cancelled', 'Cancelled'),
    )

    product = models.ForeignKey(Product, related_name='purchase_orders', on_delete=models.CASCADE)
    supplier_email = models.EmailField(default='supplier@example.com')
    requested_quantity = models.PositiveIntegerField(default=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"PO #{self.id} for {self.product.name}"
