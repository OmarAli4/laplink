from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Category, SubCategory, Product, Banner, Brand, ProductImage, ProductSpec, Announcement


from django.utils.html import format_html


class SubCategoryInline(TabularInline):
    model = SubCategory
    extra = 2
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'subcategories_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    inlines = [SubCategoryInline]

    def subcategories_count(self, obj):
        return obj.subcategories.count()
    subcategories_count.short_description = "Subcategories"


@admin.register(SubCategory)
class SubCategoryAdmin(ModelAdmin):
    list_display = ['icon_display', 'name', 'name_ar', 'category', 'slug', 'order', 'products_count']
    list_display_links = ['icon_display', 'name']
    list_editable = ['order']
    list_filter = ['category']
    search_fields = ['name', 'name_ar', 'category__name']
    prepopulated_fields = {'slug': ('name',)}

    def icon_display(self, obj):
        return format_html('<span class="text-xl">{}</span>', obj.icon or '⚡')
    icon_display.short_description = "Icon"

    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = "Products"


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
    list_display = ['product_preview', 'name', 'category', 'subcategory', 'brand', 'price', 'stock_quantity', 'availability_badge', 'featured_badge']
    list_display_links = ['product_preview', 'name']
    list_editable = ['price', 'stock_quantity']
    list_filter = ['available', 'is_featured', 'category', 'subcategory', 'brand', 'created']
    search_fields = ['name', 'description']
    @admin.action(description="✨ Standardize Titles with AI (Clean English Format)")
    def standardize_titles_with_ai(self, request, queryset):
        from .ai_service import batch_standardize_product_titles
        from django.utils.text import slugify

        products_list = list(queryset.select_related('category', 'brand').prefetch_related('specs'))
        batch_size = 15
        total_updated = 0

        for i in range(0, len(products_list), batch_size):
            batch = products_list[i:i + batch_size]
            payload = []
            for p in batch:
                specs_dict = {s.name: s.value for s in p.specs.all()[:5]}
                payload.append({
                    'id': p.id,
                    'name': p.name,
                    'category': p.category.name if p.category else '',
                    'brand': p.brand.name if p.brand else '',
                    'description': p.description[:200] if p.description else '',
                    'specs': specs_dict
                })
            
            title_map = batch_standardize_product_titles(payload)
            for p in batch:
                new_title = title_map.get(p.id)
                if new_title and new_title != p.name:
                    p.name = new_title
                    new_slug = slugify(new_title)
                    if new_slug:
                        p.slug = new_slug[:190]
                    p.save(update_fields=['name', 'slug'])
                    total_updated += 1

        self.message_user(request, f"Successfully standardized {total_updated} product titles into clean English format.")

    @admin.action(description="🤖 Run AI Vision Tagging (Extract Colors & Specs)")
    def run_ai_vision_tagging(self, request, queryset):
        from .ai_service import analyze_product_images_with_vision
        success_count = 0
        for product in queryset:
            res = analyze_product_images_with_vision(product.id)
            if res.get('success'):
                success_count += 1
        self.message_user(request, f"AI Vision successfully analyzed and tagged {success_count} products.")

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

    actions = [standardize_titles_with_ai, run_ai_vision_tagging, apply_10_percent_discount, increase_10_percent_price]
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

