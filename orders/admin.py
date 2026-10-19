import csv
import datetime
from django.contrib import admin, messages
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from .models import Order, OrderItem, ReturnRequest


@admin.action(description="✅ Mark selected orders as Paid (InstaPay / Cash Verified)")
def mark_as_paid(modeladmin, request, queryset):
    updated = queryset.update(paid=True, status='processing')
    modeladmin.message_user(
        request,
        f"{updated} orders marked as Paid & Processing.",
        level=messages.SUCCESS,
    )


@admin.action(description="🚚 Mark selected orders as Shipped")
def mark_as_shipped(modeladmin, request, queryset):
    updated = queryset.update(status='shipped')
    modeladmin.message_user(
        request,
        f"{updated} orders successfully marked as Shipped.",
        level=messages.SUCCESS,
    )


@admin.action(description="🖨️ Print Packing Slips (HTML)")
def print_packing_slips(modeladmin, request, queryset):
    html_content = [
        "<html><head><title>Packing Slips</title>"
        "<style>body{font-family:sans-serif;} .slip{page-break-after:always; margin-bottom:50px; border-bottom:2px dashed #ccc; padding-bottom:50px;}</style>"
        "</head><body onload='window.print()'>"
    ]
    for order in queryset.prefetch_related('items__product'):
        html_content.append("<div class='slip'>")
        html_content.append(f"<h2>Packing Slip - Order #{order.id} ({order.get_payment_method_display()})</h2>")
        html_content.append(f"<p><strong>Customer:</strong> {order.full_name}<br>")
        html_content.append(f"<strong>Phone:</strong> {order.phone}<br>")
        html_content.append(f"<strong>Address:</strong> {order.address}, {order.city}</p>")
        if order.delivery_notes:
            html_content.append(f"<p><strong>Notes:</strong> {order.delivery_notes}</p>")
        html_content.append("<h3>Items:</h3><ul>")
        for item in order.items.all():
            html_content.append(f"<li>{item.quantity}x {item.product.name} — {item.get_cost()} EGP</li>")
        html_content.append(f"</ul><p><strong>Shipping:</strong> {order.shipping_cost} EGP | <strong>Grand Total:</strong> {order.get_total_cost()} EGP</p></div>")
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
    extra = 0


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = [
        'id',
        'full_name_display',
        'phone',
        'city',
        'payment_method_badge',
        'proof_badge',
        'total_cost_display',
        'status_badge',
        'paid_badge',
        'created',
        'pdf_invoice',
    ]
    list_display_links = ['id', 'full_name_display']
    list_filter = ['payment_method', 'paid', 'status', 'city', 'created']
    search_fields = ['id', 'first_name', 'last_name', 'phone', 'email', 'instapay_reference']
    readonly_fields = ['created', 'updated', 'payment_proof_preview']
    inlines = [OrderItemInline]
    actions = [mark_as_paid, mark_as_shipped, print_packing_slips, export_to_csv]
    change_list_template = 'admin/orders/order/change_list.html'

    @admin.display(description="Customer")
    def full_name_display(self, obj):
        return obj.full_name or f"Order #{obj.id}"

    @admin.display(description="Payment")
    def payment_method_badge(self, obj):
        if obj.payment_method == 'instapay':
            return format_html(
                '<span class="px-2.5 py-1 bg-purple-100 text-purple-800 text-xs rounded-full font-bold">{}</span>',
                '⚡ InstaPay',
            )
        return format_html(
            '<span class="px-2.5 py-1 bg-slate-100 text-slate-800 text-xs rounded-full font-semibold">{}</span>',
            '💵 COD',
        )

    @admin.display(description="Receipt / Ref")
    def proof_badge(self, obj):
        if obj.payment_proof and getattr(obj.payment_proof, 'name', ''):
            try:
                return format_html(
                    '<a href="{}" target="_blank" class="px-2.5 py-1 bg-blue-600 text-white text-xs rounded-full font-bold">{}</a>',
                    obj.payment_proof.url,
                    '📸 View Proof',
                )
            except Exception:
                pass
        if obj.instapay_reference:
            return obj.instapay_reference
        return "—"

    @admin.display(description="InstaPay Receipt Preview")
    def payment_proof_preview(self, obj):
        if obj.payment_proof and getattr(obj.payment_proof, 'name', ''):
            try:
                return format_html(
                    '<a href="{}" target="_blank">'
                    '<img src="{}" style="max-height: 280px; border-radius: 8px; border: 1px solid #cbd5e1;" />'
                    '</a>',
                    obj.payment_proof.url,
                    obj.payment_proof.url,
                )
            except Exception:
                return "Receipt file unavailable"
        return "No receipt uploaded"

    @admin.display(description="Grand Total")
    def total_cost_display(self, obj):
        return f"{obj.get_total_cost()} EGP"

    @admin.display(description="Status")
    def status_badge(self, obj):
        return obj.get_status_display()

    @admin.display(description="Paid Status")
    def paid_badge(self, obj):
        return "✅ Paid" if obj.paid else "⏳ Unpaid"

    @admin.display(description="Order Link")
    def pdf_invoice(self, obj):
        url = reverse('orders:order_track', args=[obj.id])
        return format_html(
            '<a href="{}" target="_blank" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs rounded-full font-semibold transition-colors shadow-sm">{}</a>',
            url,
            'Track / Slip',
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request).prefetch_related('items')
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
