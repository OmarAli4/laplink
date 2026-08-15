import io
import os
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse


def optimize_image_to_webp(image_field, max_dimension=1200, quality=82):
    """
    Optimizes an uploaded image file:
    1. Resizes large dimensions (max_dimension px on longest side).
    2. Converts to modern WebP format.
    3. Retains alpha transparency if RGBA / P mode.
    4. Replaces the file with the compressed WebP ContentFile.
    """
    if not image_field or not hasattr(image_field, 'file'):
        return
    try:
        if image_field.name and image_field.name.lower().endswith('.webp'):
            return

        img = Image.open(image_field)
        
        # Handle orientation if EXIF metadata present
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass

        # Handle color modes
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')

        # Resize if oversized
        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        output_io = io.BytesIO()
        img.save(output_io, format='WEBP', quality=quality, method=6, optimize=True)
        output_io.seek(0)

        # Generate new filename with .webp
        base_name, _ = os.path.splitext(image_field.name)
        new_name = f"{base_name}.webp"

        image_field.save(new_name, ContentFile(output_io.getvalue()), save=False)
    except Exception as e:
        print(f"[Image Optimization Error]: {e}")


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    brands = models.ManyToManyField('Brand', related_name='categories', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Brand(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(upload_to='brands/%Y/%m/%d', blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.logo:
            optimize_image_to_webp(self.logo, max_dimension=400, quality=85)
        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        Category, related_name='products', on_delete=models.CASCADE
    )
    brand = models.ForeignKey(
        Brand, related_name='products', on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_start = models.DateTimeField(null=True, blank=True, db_index=True)
    sale_end = models.DateTimeField(null=True, blank=True, db_index=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show this product on the home page")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['available', 'is_featured']),
            models.Index(fields=['available', 'category']),
            models.Index(fields=['available', 'brand']),
            models.Index(fields=['created']),
        ]

    def __str__(self):
        return self.name

    @property
    def is_on_sale(self):
        """Check if product is currently within a valid sale window."""
        from django.utils import timezone
        if self.sale_price and self.sale_start and self.sale_end:
            now = timezone.now()
            return self.sale_start <= now <= self.sale_end
        return False

    @property
    def current_price(self):
        """Returns sale_price if active, else base price."""
        if self.is_on_sale:
            return self.sale_price
        return self.price

    @property
    def discount_percentage(self):
        """Returns the integer percentage of the discount."""
        if self.is_on_sale and self.price > 0:
            return int(((self.price - self.sale_price) / self.price) * 100)
        return 0

    @property
    def average_rating(self):
        from django.db.models import Avg
        result = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(result, 1) if result else 0.0

    @property
    def review_count(self):
        return self.reviews.count()

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])

    def save(self, *args, **kwargs):
        if self.image:
            optimize_image_to_webp(self.image, max_dimension=1200, quality=82)
        super().save(*args, **kwargs)


class Banner(models.Model):
    title = models.CharField(max_length=200, help_text="Internal name for the banner")
    image = models.ImageField(upload_to='banners/%Y/%m/%d')
    link = models.URLField(blank=True, help_text="Optional URL to redirect when clicked")
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Order in which banners are displayed (lowest first)")

    class Meta:
        ordering = ['order', '-id']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.image:
            optimize_image_to_webp(self.image, max_dimension=1600, quality=82)
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/%Y/%m/%d')
    alt_text = models.CharField(max_length=200, blank=True, help_text="Text for screen readers and SEO")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.image:
            optimize_image_to_webp(self.image, max_dimension=1200, quality=82)
        super().save(*args, **kwargs)


class Wishlist(models.Model):
    from django.conf import settings
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='wishlist', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='wishlisted_by', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s wishlist item: {self.product.name}"


from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', related_name='reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}"



class ProductSpec(models.Model):
    product = models.ForeignKey(Product, related_name='specs', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="e.g. RAM, CPU, Storage, Battery")
    value = models.CharField(max_length=200, help_text="e.g. 16 GB DDR5, Intel i7-13700H")
    numeric_value = models.FloatField(null=True, blank=True, help_text="Numeric value for comparison, e.g. 16 for 16GB")
    unit = models.CharField(max_length=50, blank=True, help_text="e.g. GB, GHz, mAh, hrs")
    icon = models.CharField(max_length=10, blank=True, default="⚡", help_text="Emoji or icon code")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"


class Announcement(models.Model):
    message = models.CharField(max_length=255, help_text="Text of the announcement")
    is_active = models.BooleanField(default=True, help_text="Toggle to show/hide this announcement")
    order = models.PositiveIntegerField(default=0, help_text="Order in which announcements appear")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"

    def __str__(self):
        return self.message
