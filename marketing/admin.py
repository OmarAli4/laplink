from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import FlashSale, CouponBatch

@admin.action(description="Apply flash sale to products now")
def trigger_flash_sale_apply(modeladmin, request, queryset):
    for sale in queryset:
        sale.apply_to_products()
    modeladmin.message_user(request, "Flash sale discounts applied to products successfully.")

@admin.register(FlashSale)
class FlashSaleAdmin(ModelAdmin):
    list_display = ['name', 'discount_percentage', 'start_time', 'end_time', 'is_active']
    list_filter = ['is_active', 'start_time']
    search_fields = ['name']
    actions = [trigger_flash_sale_apply]
    filter_horizontal = ['categories', 'specific_products']

@admin.action(description="Generate coupon codes for batch")
def trigger_coupon_generation(modeladmin, request, queryset):
    for batch in queryset:
        batch.generate_codes()
    modeladmin.message_user(request, "Coupons generated successfully.")

@admin.register(CouponBatch)
class CouponBatchAdmin(ModelAdmin):
    list_display = ['name', 'prefix', 'quantity', 'discount_percentage', 'generated']
    list_filter = ['generated']
    actions = [trigger_coupon_generation]
    readonly_fields = ['generated']
