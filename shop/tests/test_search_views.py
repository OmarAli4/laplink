from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from shop.models import Category, SubCategory, Brand, Product
from shop.search import index_products, invalidate_cache


@override_settings(
    SEARCH_AUTO_INDEX_ON_SAVE=False,
    SEARCH_SEMANTIC_MIN_SIM=0.5,
    SEARCH_ENABLE_SEMANTIC=True,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class SearchViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat_audio = Category.objects.create(name="Audio", slug="audio")
        cat_bags = Category.objects.create(name="Bags", slug="bags")
        cat_laptops = Category.objects.create(name="Laptops", slug="laptops")

        brand_apple = Brand.objects.create(name="Apple", slug="apple")
        brand_sony = Brand.objects.create(name="Sony", slug="sony")
        brand_bange = Brand.objects.create(name="Bange", slug="bange")

        cls.p_airpods = Product.objects.create(
            name="Apple AirPods Pro 2",
            slug="apple-airpods-pro-2",
            category=cat_audio,
            brand=brand_apple,
            description="Wireless noise cancelling earbuds.",
            price=250.00,
            available=True,
            search_tags="headphones, earbuds, سماعات",
            search_embedding=[1.0, 0.0, 0.0, 0.0]
        )

        cls.p_sony = Product.objects.create(
            name="Sony WH-1000XM5",
            slug="sony-wh-1000xm5",
            category=cat_audio,
            brand=brand_sony,
            description="Over ear wireless headset.",
            price=399.00,
            available=True,
            search_tags="headphones, headset, سماعات",
            search_embedding=[1.0, 0.0, 0.0, 0.0]
        )

        cls.p_bange = Product.objects.create(
            name="Bange Travel Laptop Backpack",
            slug="bange-travel-laptop-backpack",
            category=cat_bags,
            brand=brand_bange,
            description="Waterproof backpack for laptop.",
            price=50.00,
            available=True,
            search_tags="backpack, bag, شنطة لابتوب",
            search_embedding=[0.0, 1.0, 0.0, 0.0]
        )

        cls.cat_laptops = cat_laptops
        cls.brand_apple = brand_apple
        cls.brand_sony = brand_sony

        index_products(Product.objects.all(), use_ai=False)
        invalidate_cache()

    def setUp(self):
        self.client = Client()
        invalidate_cache()

    def test_catalog_search_backpacks(self):
        url = reverse('shop:product_list')
        response = self.client.get(url, {'q': 'backpacks'})
        self.assertEqual(response.status_code, 200)
        prods = list(response.context['products'])
        self.assertIn(self.p_bange, prods)

    @patch('shop.search.semantic.gemini.embed_query')
    def test_catalog_category_scope_expanded_notice(self, mock_embed):
        mock_embed.return_value = [1.0, 0.0, 0.0, 0.0]
        url = reverse('shop:product_list_by_category', kwargs={'category_slug': 'laptops'})
        response = self.client.get(url, {'q': 'headphone'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context.get('search_scope_expanded'))
        # Check notice in HTML
        self.assertContains(response, "showing results from the whole store")

    def test_catalog_multi_brand_filter_and_sort(self):
        url = reverse('shop:product_list')
        response = self.client.get(f"{url}?brand=apple&brand=sony&sort=price_asc")
        self.assertEqual(response.status_code, 200)
        prods = list(response.context['products'])
        self.assertEqual(len(prods), 2)
        self.assertIn(self.p_airpods, prods)
        self.assertIn(self.p_sony, prods)

        content = response.content.decode('utf-8')
        # Rendered sort <option> values must contain both brand=apple and brand=sony
        self.assertIn("brand=apple", content)
        self.assertIn("brand=sony", content)

    def test_search_autocomplete(self):
        url = reverse('shop:search_autocomplete')
        response = self.client.get(url, {'q': 'ba'})
        self.assertEqual(response.status_code, 200)

    def test_catalog_search_xss_escaped(self):
        url = reverse('shop:product_list')
        response = self.client.get(url, {'q': '<script>alert(1)</script>'})
        self.assertEqual(response.status_code, 200)
        # Content should escape HTML
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_homepage_ux_sections_and_no_giant_hero_text(self):
        url = reverse('shop:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Verify old giant hero text is removed
        self.assertNotContains(response, "Where Elite Tech Meets")
        # Verify new UX elements exist in context and HTML
        self.assertIn('catalog_tabs', response.context)
        self.assertIn('quick_searches', response.context)
        self.assertContains(response, 'id="home-search-results"')
        self.assertContains(response, "Shop by Category")
