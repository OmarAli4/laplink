from django.contrib import admin
from django.contrib.admin import ModelAdmin
from .models import Coupon




@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = ['code', 'discount', 'free_shipping_badge', 'valid_from', 'valid_to', 'usage_limit', 'times_used', 'status_badge']
    list_filter = ['active', 'is_free_shipping', 'valid_from', 'valid_to']
    search_fields = ['code', 'description']
    readonly_fields = ['times_used']
    
    fieldsets = (
        ('Coupon Details', {
            'fields': ('code', 'description', 'active')
        }),
        ('Discount & Perks', {
            'fields': ('discount', 'is_free_shipping')
        }),
        ('Rules & Limits', {
            'fields': ('valid_from', 'valid_to', 'usage_limit')
        }),
        ('Analytics', {
            'fields': ('times_used',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj):
        return "Active" if obj.active else "Expired"

    @admin.display(description="Free Shipping")
    def free_shipping_badge(self, obj):
        return "Free Shipping" if obj.is_free_shipping else "Standard Shipping"
