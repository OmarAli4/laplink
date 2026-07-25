import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
django.setup()

from django.core.files import File
from shop.models import Banner

paths = {
    'apple': r'C:\Users\Dr. Wesam\.gemini\antigravity\brain\b40dcb5d-f311-4a52-8099-ca83112360aa\banner_all_logos_1783088147607.png',
    'google': r'C:\Users\Dr. Wesam\.gemini\antigravity\brain\b40dcb5d-f311-4a52-8099-ca83112360aa\banner_sam_google_1783088166438.png',
    'samsung': r'C:\Users\Dr. Wesam\.gemini\antigravity\brain\b40dcb5d-f311-4a52-8099-ca83112360aa\banner_apple_logo_1783088155993.png',
    'rtx': r'C:\Users\Dr. Wesam\.gemini\antigravity\brain\b40dcb5d-f311-4a52-8099-ca83112360aa\banner_rtx_logo_1783088177451.png',
}

for title, path in paths.items():
    banner = Banner.objects.filter(title__icontains=title).first()
    if banner and os.path.exists(path):
        with open(path, 'rb') as f:
            banner.image.save(f'{title}_logo_banner.png', File(f), save=True)
            print(f"Updated banner: {title}")
