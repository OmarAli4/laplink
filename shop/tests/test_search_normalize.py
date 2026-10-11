from django.test import SimpleTestCase
from shop.search.normalize import normalize, tokenize, stem


class SearchNormalizeTests(SimpleTestCase):
    def test_normalize_arabic_letters_and_diacritics(self):
        self.assertEqual(normalize("أحمد"), "احمد")
        self.assertEqual(normalize("إبراهيم"), "ابراهيم")
        self.assertEqual(normalize("آبل"), "ابل")
        self.assertEqual(normalize("سمّاعة"), "سماعه")
        self.assertEqual(normalize("موسيقى"), "موسيقي")
        self.assertEqual(normalize("مسؤول"), "مسوول")
        self.assertEqual(normalize("شاطئ"), "شاطي")

    def test_normalize_digits(self):
        self.assertEqual(normalize("١٥.٦"), "15.6")
        self.assertEqual(normalize("سعر ٥٠٠ ج"), "سعر 500 ج")

    def test_normalize_punctuation_and_whitespace(self):
        self.assertEqual(normalize("Wireless!!  Earbuds"), "wireless earbuds")
        self.assertEqual(normalize("Sony   WH-1000XM5..."), "sony wh-1000xm5")
        self.assertEqual(normalize(None), "")
        self.assertEqual(normalize(""), "")

    def test_tokenize_hyphen_and_dots(self):
        tokens = tokenize("WH-1000XM5")
        self.assertTrue({"wh-1000xm5", "wh1000xm5", "wh", "1000xm5"}.issubset(set(tokens)))

        tokens_usb = tokenize("USB-C")
        self.assertTrue({"usb-c", "usbc", "usb"}.issubset(set(tokens_usb)))
        self.assertNotIn("c", tokens_usb)  # Single character dropped

    def test_tokenize_decimal_numbers(self):
        tokens = tokenize("Laptop 15.6 inch")
        self.assertIn("15.6", tokens)

    def test_tokenize_arabic_prefixes(self):
        tokens_al = tokenize("الشاحن")
        self.assertTrue({"الشاحن", "شاحن"}.issubset(set(tokens_al)))

        tokens_wa = tokenize("والشاحن")
        self.assertIn("شاحن", tokens_wa)

    def test_stemming_english(self):
        self.assertEqual(stem("backpacks"), "backpack")
        self.assertEqual(stem("batteries"), "battery")
        self.assertEqual(stem("boxes"), "box")
        self.assertEqual(stem("watches"), "watch")
        self.assertEqual(stem("glasses"), "glass")
        self.assertEqual(stem("glass"), "glass")  # Double 's' not stripped
        self.assertEqual(stem("yes"), "yes")      # Length <= 3 not stripped

    def test_stemming_arabic(self):
        self.assertEqual(stem("سماعات"), "سماع")
        self.assertEqual(stem("شنطه"), "شنط")
        self.assertEqual(stem("شواحن"), "شواحن")  # Doesn't end in ات or ه
