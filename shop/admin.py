from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Category, Product, Banner, Brand, ProductImage, ProductSpec, Announcement


from django.utils.html import format_html


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ['logo_preview', 'name', 'slug']
    list_display_links = ['logo_preview', 'name']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" class="w-8 h-8 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shadow-sm" />', obj.logo.url)
        return "—"
    logo_preview.short_description = "Logo"


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 3


class ProductSpecInline(TabularInline):
    model = ProductSpec
    extra = 4


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['product_preview', 'name', 'category', 'brand', 'price', 'stock_quantity', 'availability_badge', 'featured_badge']
    list_display_links = ['product_preview', 'name']
    list_editable = ['price', 'stock_quantity']
    list_filter = ['available', 'is_featured', 'category', 'brand', 'created']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    @admin.action(description="Decrease Price by 10%% (Sale)")
    def apply_10_percent_discount(self, request, queryset):
        for product in queryset:
            product.price = float(product.price) * 0.90
            product.save(update_fields=['price'])
        self.message_user(request, "10% discount applied to selected products.")

    @admin.action(description="Increase Price by 10%%")
    def increase_10_percent_price(self, request, queryset):
        for product in queryset:
            product.price = float(product.price) * 1.10
            product.save(update_fields=['price'])
        self.message_user(request, "Price increased by 10% for selected products.")

    actions = [apply_10_percent_discount, increase_10_percent_price]
    inlines = [ProductImageInline, ProductSpecInline]
    
    fieldsets = (
        ('General Information', {
            'fields': ('category', 'brand', 'name', 'slug', 'image', 'description')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'sale_price', 'sale_start', 'sale_end', 'stock_quantity', 'available')
        }),
        ('Display Settings', {
            'fields': ('is_featured',)
        }),
    )

    def product_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="w-10 h-10 rounded-lg object-contain bg-slate-100 dark:bg-slate-800 p-1 border border-slate-200 dark:border-slate-700 shadow-sm" />', obj.image.url)
        return "📦"
    product_preview.short_description = "Image"

    @admin.display(description="Status")
    def availability_badge(self, obj):
        return "In Stock" if obj.available else "Out of Stock"

    @admin.display(description="Featured")
    def featured_badge(self, obj):
        return "Featured" if obj.is_featured else "Standard"


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ['title', 'status_badge', 'order']
    list_filter = ['active']
    search_fields = ['title']

    @admin.display(description="Active")
    def status_badge(self, obj):
        return "Live" if obj.active else "Inactive"


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    list_display = ['message', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['message']


from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import TabularInline
from orders.models import Order


class UserOrderInline(TabularInline):
    model = Order
    fields = ['id', 'created', 'paid', 'total_cost']
    readonly_fields = ['id', 'created', 'paid', 'total_cost']
    can_delete = False
    extra = 0

    def total_cost(self, obj):
        return f"${obj.get_total_cost():.2f}"
    total_cost.short_description = 'Total Cost'

    def has_add_permission(self, request, obj=None):
        return False


admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = [UserOrderInline]

