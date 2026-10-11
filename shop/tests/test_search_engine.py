import unittest
from unittest.mock import patch
from django.test import TestCase, override_settings

from shop.models import Category, SubCategory, Brand, Product, ProductSpec
from shop.search import search, index_products, invalidate_cache


@override_settings(
    SEARCH_AUTO_INDEX_ON_SAVE=False,
    SEARCH_SEMANTIC_MIN_SIM=0.5,
    SEARCH_ENABLE_SEMANTIC=True,
    SEARCH_RRF_K=60
)
class SearchEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Categories
        cat_audio = Category.objects.create(name="Audio", slug="audio")
        cat_bags = Category.objects.create(name="Bags", slug="bags")
        cat_charging = Category.objects.create(name="Charging", slug="charging")
        cat_acc = Category.objects.create(name="Computer Accessories", slug="computer-accessories")
        cat_laptops = Category.objects.create(name="Laptops", slug="laptops")

        # 2. SubCategories
        sub_earbuds = SubCategory.objects.create(category=cat_audio, name="Wireless Earbuds", slug="wireless-earbuds")
        sub_overear = SubCategory.objects.create(category=cat_audio, name="Over-Ear", slug="over-ear")
        sub_gaming = SubCategory.objects.create(category=cat_laptops, name="Gaming", slug="gaming")

        # 3. Brands
        brand_apple = Brand.objects.create(name="Apple", slug="apple")
        brand_sony = Brand.objects.create(name="Sony", slug="sony")
        brand_bange = Brand.objects.create(name="Bange", slug="bange")
        brand_anker = Brand.objects.create(name="Anker", slug="anker")
        brand_logi = Brand.objects.create(name="Logitech", slug="logitech")
        brand_lenovo = Brand.objects.create(name="Lenovo", slug="lenovo")

        # 4. Products
        cls.p_airpods = Product.objects.create(
            name="Apple AirPods Pro 2 USB-C",
            slug="apple-airpods-pro-2-usb-c",
            category=cat_audio,
            subcategory=sub_earbuds,
            brand=brand_apple,
            description="Wireless earbuds with active noise cancellation and spatial audio.",
            price=250.00,
            available=True,
            search_embedding=[1.0, 0.0, 0.0, 0.0]  # Audio concept
        )
        ProductSpec.objects.create(product=cls.p_airpods, name="Connectivity", value="Bluetooth 5.3", order=1)

        cls.p_sony = Product.objects.create(
            name="Sony WH-1000XM5",
            slug="sony-wh-1000xm5",
            category=cat_audio,
            subcategory=sub_overear,
            brand=brand_sony,
            description="Noise cancelling wireless over-ear headset.",
            price=399.00,
            available=True,
            search_embedding=[1.0, 0.0, 0.0, 0.0]  # Audio concept
        )
        ProductSpec.objects.create(product=cls.p_sony, name="Battery", value="30 hours", order=1)

        cls.p_bange = Product.objects.create(
            name="Bange 1908 Waterproof Travel Laptop Backpack",
            slug="bange-1908-waterproof-travel-laptop-backpack",
            category=cat_bags,
            brand=brand_bange,
            description="Anti-theft business bag for 15.6 inch laptops.",
            price=45.00,
            available=True,
            search_embedding=[0.0, 1.0, 0.0, 0.0]  # Bags concept
        )
        ProductSpec.objects.create(product=cls.p_bange, name="Water Resistance", value="IPX6", order=1)

        cls.p_anker = Product.objects.create(
            name="Anker 737 Power Bank 24K",
            slug="anker-737-power-bank-24k",
            category=cat_charging,
            brand=brand_anker,
            description="140W portable charger with smart display.",
            price=149.00,
            available=True,
            search_embedding=[0.0, 0.0, 1.0, 0.0]  # Charging concept
        )
        ProductSpec.objects.create(product=cls.p_anker, name="Capacity", value="24000 mAh", order=1)

        cls.p_mouse = Product.objects.create(
            name="Logitech MX Master 3S Mouse",
            slug="logitech-mx-master-3s-mouse",
            category=cat_acc,
            brand=brand_logi,
            description="Ergonomic wireless mouse.",
            price=99.00,
            available=True,
            search_embedding=[0.0, 0.0, 0.0, 1.0]  # Computing concept
        )
        ProductSpec.objects.create(product=cls.p_mouse, name="DPI", value="8000", order=1)

        cls.p_laptop = Product.objects.create(
            name="Lenovo Legion 5 Gaming Laptop",
            slug="lenovo-legion-5-gaming-laptop",
            category=cat_laptops,
            subcategory=sub_gaming,
            brand=brand_lenovo,
            description="RTX 4060 gaming laptop.",
            price=1200.00,
            available=True,
            search_embedding=[0.0, 0.0, 0.0, 1.0]  # Computing concept
        )
        ProductSpec.objects.create(product=cls.p_laptop, name="RAM", value="16 GB", order=1)

        cls.cat_laptops = cat_laptops

        # Populate search_tags manually to simulate AI output deterministically
        cls.p_airpods.search_tags = "headphones, earbuds, سماعات, ايربودز"
        cls.p_airpods.save(update_fields=['search_tags'])

        cls.p_sony.search_tags = "headphones, headset, over-ear, سماعات, هيدفون"
        cls.p_sony.save(update_fields=['search_tags'])

        cls.p_bange.search_tags = "backpack, bag, rucksack, شنطة لابتوب, شنطة ظهر"
        cls.p_bange.save(update_fields=['search_tags'])

        # Build search text documents
        index_products(Product.objects.all(), use_ai=False)
        invalidate_cache()

    def setUp(self):
        invalidate_cache()

    @patch('shop.search.semantic.gemini.embed_query')
    def test_T01_headphone_semantic_audio(self, mock_embed):
        # Audio concept vector
        mock_embed.return_value = [1.0, 0.0, 0.0, 0.0]
        res = search("headphone")
        self.assertIn(self.p_airpods.id, res.ids)
        self.assertIn(self.p_sony.id, res.ids)
        self.assertNotIn(self.p_bange.id, res.ids)
        self.assertNotIn(self.p_anker.id, res.ids)
        self.assertNotIn(self.p_mouse.id, res.ids)

    def test_T02_backpacks_stem(self):
        res = search("backpacks")
        self.assertIn(self.p_bange.id, res.ids)
        self.assertNotIn(self.p_airpods.id, res.ids)

    def test_T03_laptop_backpack_waterproof_ranking(self):
        res = search("laptop backpack waterproof")
        self.assertTrue(len(res.ids) > 0)
        self.assertEqual(res.ids[0], self.p_bange.id)

    def test_T04_waterproof_backpack_laptop_order_independence(self):
        r1 = search("laptop backpack waterproof")
        r2 = search("waterproof backpack laptop")
        self.assertEqual(r1.ids[0], r2.ids[0])
        self.assertEqual(r1.ids[0], self.p_bange.id)

    def test_T05_brand_field_match(self):
        res = search("sony")
        self.assertTrue(len(res.ids) > 0)
        self.assertEqual(res.ids[0], self.p_sony.id)
        self.assertNotIn(self.p_bange.id, res.ids)

    def test_T06_joined_model_token(self):
        res = search("wh1000xm5")
        self.assertIn(self.p_sony.id, res.ids)

    def test_T07_hyphen_token(self):
        res = search("WH-1000XM5")
        self.assertIn(self.p_sony.id, res.ids)

    @patch('shop.search.semantic.gemini.embed_query')
    def test_T08_fuzzy_headfone_api_down(self, mock_embed):
        mock_embed.return_value = None
        res = search("headfone")
        # Should not crash, returns list through fuzzy vocab match
        self.assertIsInstance(res.ids, list)

    def test_T09_arabic_tags(self):
        res = search("ايربودز")
        self.assertIn(self.p_airpods.id, res.ids)
        self.assertNotIn(self.p_bange.id, res.ids)
        self.assertNotIn(self.p_laptop.id, res.ids)

    def test_T10_arabic_al_prefix_and_stem(self):
        res = search("السماعات")
        self.assertIn(self.p_airpods.id, res.ids)
        self.assertNotIn(self.p_bange.id, res.ids)

    def test_T11_no_substring_false_positive_anc(self):
        # 'anc' should not match 'Water Resistance' in bange
        res = search("anc")
        self.assertNotIn(self.p_bange.id, res.ids)

    @patch('shop.search.semantic.gemini.embed_query')
    def test_T12_category_scope_fallback(self, mock_embed):
        mock_embed.return_value = [1.0, 0.0, 0.0, 0.0]
        # Querying headphone inside Laptops category should fallback to store
        res = search("headphone", category=self.cat_laptops)
        self.assertTrue(res.scope_expanded)
        self.assertIn(self.p_airpods.id, res.ids)

    def test_T13_normal_category_scope(self):
        res = search("gaming", category=self.cat_laptops)
        self.assertFalse(res.scope_expanded)
        self.assertIn(self.p_laptop.id, res.ids)

    def test_T14_specs_field_match(self):
        res = search("bluetooth 5.3")
        self.assertIn(self.p_airpods.id, res.ids)

    def test_T15_empty_query(self):
        res = search("")
        self.assertEqual(res.mode, "empty")
        self.assertEqual(res.ids, [])

    @patch('shop.search.semantic.gemini.embed_query')
    def test_T16_nonsense_query_returns_empty(self, mock_embed):
        # Low similarity vector below threshold 0.5
        mock_embed.return_value = [0.1, 0.1, 0.1, 0.1]
        res = search("zzzqqq")
        self.assertEqual(res.ids, [])

    @patch('shop.search.semantic.gemini.embed_query')
    def test_T17_fail_soft_when_gemini_none(self, mock_embed):
        mock_embed.return_value = None
        res = search("backpack")
        self.assertEqual(res.mode, "keyword")
        self.assertIn(self.p_bange.id, res.ids)
