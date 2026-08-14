import csv
import datetime
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem, ReturnRequest

@admin.action(description="Mark selected orders as Shipped")
def mark_as_shipped(modeladmin, request, queryset):
    updated = queryset.update(status='shipped')
    modeladmin.message_user(request, f"{updated} orders successfully marked as Shipped.", level='SUCCESS')

@admin.action(description="Print Packing Slips (HTML)")
def print_packing_slips(modeladmin, request, queryset):
    # Generates a print-ready HTML page for the selected orders
    html_content = ["<html><head><title>Packing Slips</title><style>body{font-family:sans-serif;} .slip{page-break-after:always; margin-bottom:50px; border-bottom:2px dashed #ccc; padding-bottom:50px;}</style></head><body onload='window.print()'>"]
    for order in queryset:
        html_content.append(f"<div class='slip'>")
        html_content.append(f"<h2>Packing Slip - Order #{order.id}</h2>")
        html_content.append(f"<p><strong>Customer:</strong> {order.first_name} {order.last_name}<br>")
        html_content.append(f"<strong>Email:</strong> {order.email}<br>")
        html_content.append(f"<strong>Address:</strong> {order.address}, {order.city} {order.postal_code}</p>")
        html_content.append(f"<h3>Items:</h3><ul>")
        for item in order.items.all():
            html_content.append(f"<li>{item.quantity}x {item.product.name} (SKU: {item.product.slug})</li>")
        html_content.append("</ul></div>")
    html_content.append("</body></html>")
    return HttpResponse("".join(html_content))
def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f'attachment; filename={opts.verbose_name}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content_disposition
    writer = csv.writer(response)
    fields = [field for field in opts.get_fields() if not field.many_to_many and not field.one_to_many]
    writer.writerow([field.verbose_name for field in fields])
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime.datetime):
                value = value.strftime('%d/%m/%Y')
            data_row.append(value)
        writer.writerow(data_row)
    return response

export_to_csv.short_description = 'Export to CSV'




class OrderItemInline(TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['id', 'user', 'first_name', 'last_name', 'email', 'phone', 'status_badge', 'paid_badge', 'created', 'pdf_invoice']
    list_filter = ['status', 'paid', 'created', 'updated']
    inlines = [OrderItemInline]
    actions = [export_to_csv, mark_as_shipped, print_packing_slips]
    change_list_template = 'admin/orders/order/change_list.html'

    @admin.display(description="Status")
    def status_badge(self, obj):
        return obj.status

    @admin.display(description="Paid Status")
    def paid_badge(self, obj):
        return "Paid" if obj.paid else "Unpaid"

    def pdf_invoice(self, obj):
        return format_html(
            '<a href="#" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs rounded-full font-semibold transition-colors shadow-sm">{}</a>',
            'Download PDF'
        )
    pdf_invoice.short_description = 'Invoice'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Calculate revenue for the changelist
        # For a production app with many orders, this should use DB aggregation.
        # Since get_total_cost() is a model method relying on related objects, we iterate.
        qs = self.get_queryset(request)
        total_orders = qs.count()
        total_revenue = sum(order.get_total_cost() for order in qs)
        
        extra_context['total_orders'] = total_orders
        extra_context['total_revenue'] = total_revenue
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ReturnRequest)
class ReturnRequestAdmin(ModelAdmin):
    list_display = ['id', 'order', 'user', 'status', 'created']
    list_filter = ['status', 'created']
    search_fields = ['order__id', 'user__email', 'reason']
    list_editable = ['status']
