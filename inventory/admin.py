from django.contrib import admin
from .models import InventoryLog, PurchaseOrder

@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'quantity_change', 'reason', 'user', 'timestamp']
    list_filter = ['reason', 'timestamp']
    search_fields = ['product__name', 'user__username', 'note']
    readonly_fields = ['product', 'quantity_change', 'reason', 'user', 'timestamp', 'note']
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'supplier_email', 'requested_quantity', 'status', 'created']
    list_filter = ['status', 'created']
    list_editable = ['status']
    search_fields = ['product__name', 'supplier_email']
