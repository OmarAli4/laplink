from django.contrib import admin
from .models import CustomerProfile, SupportTicket

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_vip', 'lifetime_value', 'total_orders', 'last_order_date']
    list_filter = ['is_vip']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user', 'lifetime_value', 'total_orders', 'last_order_date']

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'user', 'order', 'status', 'created']
    list_filter = ['status', 'created']
    search_fields = ['subject', 'user__email', 'order__id']
    list_editable = ['status']
