import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv
from django.utils.translation import gettext as _
from .models import Product

# Ensure .env is always freshly loaded
load_dotenv(override=True)


def get_in_stock_catalog():
    """
    Extract a comprehensive JSON list of available in-stock products with specs, categories, and descriptions.
    """
    products = Product.objects.filter(available=True).select_related('category', 'brand').prefetch_related('specs')
    catalog = []
    for p in products:
        specs_dict = {s.name: s.value for s in p.specs.all()}
        catalog.append({
            "id": p.id,
            "name": p.name,
            "brand": p.brand.name if p.brand else "",
            "category": p.category.name if p.category else "",
            "price": float(p.current_price),
            "specs": specs_dict,
            "description": p.description[:400] if p.description else ""
        })
    return catalog


def ask_ai_tech_finder(user_prompt: str):
    """
    Pure Google Gemini LLM API Recommendation Engine.
    Directly analyzes user intent, use-case, and constraints across all store inventory.
    """
    load_dotenv(override=True)
    catalog = get_in_stock_catalog()
    if not catalog:
        return {
            "success": False,
            "error": _("No in-stock products available right now.")
        }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "error": _("Gemini API key is missing. Please configure GEMINI_API_KEY in .env.")
        }

    # Gemini System Instruction
    system_instruction = (
        "You are Lap Link AI Finder, an elite AI tech matchmaker in Egypt.\n"
        "Our store sells all tech categories: Laptops, Laptop Bags & Sleeves (شنط وجرابات), Mobile Accessories, Cables, Chargers, and Computer Peripherals.\n\n"
        "A customer has asked: '" + user_prompt + "'.\n\n"
        "Here is our complete in-stock product catalog:\n"
        f"{json.dumps(catalog, ensure_ascii=False)}\n\n"
        "Instructions:\n"
        "1. Search across ALL product categories (Laptops, Bags, Accessories, Chargers, etc.) for products matching the customer's intent, category, color, brand, or budget.\n"
        "2. If the user asks for a category (e.g. 'شنطة', 'bag', 'جراب', 'شاحن', 'لابتوب'), inspect all products in that category and match the closest items.\n"
        "3. If the user asks for a specific brand (e.g. Apple, Elite, Bange, ASUS, Lenovo), ONLY return products of that brand strictly.\n"
        "4. If the user asks for 'all' or plural items (e.g. 'كل اللابات', 'كل الشنط'), return all matching product IDs in `product_ids`.\n"
        "5. If matching products are found, return their IDs in `product_ids`.\n"
        "6. If NO matching product exists in the catalog, return `product_ids: []`, `product_id: null`, `match_score: 0`, and politely explain what is currently available in friendly Egyptian Arabic.\n"
        "7. Reply in the EXACT same dialect as the customer (friendly, polite Egyptian Arabic if Arabic, or English if English).\n"
        "8. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "product_ids": [<list of matched integer product IDs from catalog, e.g. [1, 2] or [] if none>],\n'
        '  "product_id": <int or null: primary matched product ID>,\n'
        '  "match_score": <int: 0 if no match, 80-99 if match>,\n'
        '  "ai_message": "<string: 2-3 friendly sentences in customer language explaining the recommendation or noting what is in stock>",\n'
        '  "highlights": ["<string: key highlight 1>", "<string: key highlight 2>", "<string: key highlight 3>"]\n'
        "}"
    )

    models_to_try = ['gemini-flash-lite-latest', 'gemini-flash-latest']
    
    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": system_instruction}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 1000
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key
                }
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                
                # Strip markdown if present
                if '```json' in raw_text:
                    raw_text = raw_text.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_text:
                    raw_text = raw_text.split('```')[1].split('```')[0].strip()
                    
                parsed_data = json.loads(raw_text)
                
                # Ensure product_ids array exists
                if 'product_ids' not in parsed_data and 'product_id' in parsed_data:
                    parsed_data['product_ids'] = [parsed_data['product_id']] if parsed_data['product_id'] else []
                elif 'product_id' not in parsed_data and parsed_data.get('product_ids'):
                    parsed_data['product_id'] = parsed_data['product_ids'][0]
                    
                # Validate against in-stock catalog
                valid_ids = [pid for pid in parsed_data.get('product_ids', []) if any(p['id'] == pid for p in catalog)]
                parsed_data['product_ids'] = valid_ids
                parsed_data['product_id'] = valid_ids[0] if valid_ids else None
                
                return {"success": True, "data": parsed_data, "is_ai": True}
        except Exception as e:
            last_error = e
            print(f"[AI Tech Finder Gemini {model_name} Error]: {e}")
            continue

    return {
        "success": False,
        "error": _(f"AI service temporarily unavailable: {last_error}")
    }


def evaluate_product_duel(product_a_id: int, product_b_id: int):
    """
    AI Battle Referee that analyzes two products in the same category head-to-head.
    Returns winner, scores, category criteria scores, punchy Egyptian Arabic verdict, and best-for guidance.
    """
    load_dotenv(override=True)
    product_a = Product.objects.filter(id=product_a_id, available=True).select_related('category', 'brand').prefetch_related('specs').first()
    product_b = Product.objects.filter(id=product_b_id, available=True).select_related('category', 'brand').prefetch_related('specs').first()
    
    if not product_a or not product_b:
        return {
            "success": False,
            "error": _("One or both products were not found.")
        }
        
    # Strictly enforce same category check
    if product_a.category_id != product_b.category_id:
        return {
            "success": False,
            "error": _("Duel comparison is only allowed between products in the same category.")
        }

    specs_a = {s.name: s.value for s in product_a.specs.all()}
    specs_b = {s.name: s.value for s in product_b.specs.all()}
    
    prod_a_info = {
        "id": product_a.id,
        "name": product_a.name,
        "brand": product_a.brand.name if product_a.brand else "",
        "category": product_a.category.name if product_a.category else "",
        "price": float(product_a.current_price),
        "specs": specs_a
    }
    prod_b_info = {
        "id": product_b.id,
        "name": product_b.name,
        "brand": product_b.brand.name if product_b.brand else "",
        "category": product_b.category.name if product_b.category else "",
        "price": float(product_b.current_price),
        "specs": specs_b
    }

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {
            "success": False,
            "error": _("Gemini API key is missing.")
        }

    system_instruction = (
        f"You are the Ultimate AI Tech Referee for Lap Link Egypt. "
        f"A customer is comparing two devices in the '{product_a.category.name}' category in a head-to-head battle.\n\n"
        f"Contender A: {json.dumps(prod_a_info, ensure_ascii=False)}\n\n"
        f"Contender B: {json.dumps(prod_b_info, ensure_ascii=False)}\n\n"
        "Instructions:\n"
        "1. Perform an expert, unbiased comparison between Contender A and Contender B.\n"
        "2. Judge which device wins overall or if it is a draw/tie.\n"
        "3. Evaluate across 4 core dimensions relevant to their hardware: Performance/Processing, Display/Design, Battery/Mobility, Value-For-Money.\n"
        "4. Write an authentic, natural, friendly Egyptian Arabic technical verdict explaining clearly which device wins and who should buy each.\n"
        "5. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "winner": "<string: \'A\', \'B\', or \'TIE\'>",\n'
        '  "winner_name": "<string: exact name of winning product or \'تعادل متقارب\'>",\n'
        '  "score_a": <int: score 60-99>,\n'
        '  "score_b": <int: score 60-99>,\n'
        '  "verdict_summary": "<string: 2-3 sentences in Egyptian Arabic explaining the battle outcome and technical reasons clearly>",\n'
        '  "criteria": [\n'
        '    {"title": "الأداء والمعالجة (Performance)", "winner": "<string: \'A\', \'B\', or \'TIE\'>", "reason": "<string: short 1-line reason>"},\n'
        '    {"title": "الشاشة وجودة العرض (Display)", "winner": "<string: \'A\', \'B\', or \'TIE\'>", "reason": "<string: short 1-line reason>"},\n'
        '    {"title": "البطارية والتنقل (Mobility)", "winner": "<string: \'A\', \'B\', or \'TIE\'>", "reason": "<string: short 1-line reason>"},\n'
        '    {"title": "القيمة مقابل السعر (Value)", "winner": "<string: \'A\', \'B\', or \'TIE\'>", "reason": "<string: short 1-line reason>"}\n'
        '  ],\n'
        '  "strengths_a": ["<string: key advantage 1>", "<string: key advantage 2>", "<string: key advantage 3>"],\n'
        '  "strengths_b": ["<string: key advantage 1>", "<string: key advantage 2>", "<string: key advantage 3>"],\n'
        '  "best_for_a": "<string: مين يشتري جهاز A>",\n'
        '  "best_for_b": "<string: مين يشتري جهاز B>"\n'
        "}"
    )

    models_to_try = ['gemini-flash-lite-latest', 'gemini-flash-latest']
    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": system_instruction}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 1200
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key
                }
            )
            with urllib.request.urlopen(req, timeout=14) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                if '```json' in raw_text:
                    raw_text = raw_text.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_text:
                    raw_text = raw_text.split('```')[1].split('```')[0].strip()
                parsed_data = json.loads(raw_text)
                return {"success": True, "duel": parsed_data, "is_ai": True}
        except Exception as e:
            last_error = e
            print(f"[AI Duel Referee Gemini {model_name} Error]: {e}")
            continue

    return {
        "success": False,
        "error": _(f"AI Duel Referee temporarily unavailable: {last_error}")
    }


import base64

def analyze_product_images_with_vision(product_id: int):
    """
    Multimodal AI Vision analysis for a product across all its photos (Cover + Gallery).
    Automatically extracts accurate colors, materials, and form factor,
    and updates ProductSpec in the database.
    """
    load_dotenv(override=True)
    from .models import Product, ProductSpec
    
    product = Product.objects.filter(id=product_id).prefetch_related('images', 'specs').first()
    if not product:
        return {"success": False, "error": "Product not found"}
        
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return {"success": False, "error": "Gemini API key missing"}

    def read_image_to_part(field):
        if not field:
            return None
        try:
            if hasattr(field, 'path') and os.path.exists(field.path):
                with open(field.path, 'rb') as f:
                    data = f.read()
                    mime = 'image/webp' if field.name.lower().endswith('.webp') else 'image/jpeg'
                    return {'inline_data': {'mime_type': mime, 'data': base64.b64encode(data).decode('utf-8')}}
            if hasattr(field, 'open'):
                field.open('rb')
                data = field.read()
                mime = 'image/webp' if field.name.lower().endswith('.webp') else 'image/jpeg'
                return {'inline_data': {'mime_type': mime, 'data': base64.b64encode(data).decode('utf-8')}}
        except Exception as e:
            print(f"[Vision read error]: {e}")
        return None

    # Collect all image files
    image_parts = []
    
    # 1. Main cover image
    cover_part = read_image_to_part(product.image)
    if cover_part:
        image_parts.append(cover_part)
            
    # 2. Gallery images
    for gallery_img in product.images.all()[:4]:
        gal_part = read_image_to_part(gallery_img.image)
        if gal_part:
            image_parts.append(gal_part)
                
    if not image_parts:
        return {"success": False, "error": "No valid image files found for product"}

    prompt = (
        f"Analyze all attached photos for the product '{product.name}' in category '{product.category.name if product.category else ''}'.\n"
        "Carefully inspect the visual details across all images (colors, angles, materials, size, form-factor).\n"
        "Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "primary_color": "<string: main dominant color in Arabic & English, e.g. نبيتي أحمر / Burgundy Red>",\n'
        '  "color_palette": ["<color 1 in Arabic/English>", "<color 2>"],\n'
        '  "item_type": "<string: specific form factor e.g. شنطة كروس لابتوب / Crossbody Laptop Bag>",\n'
        '  "material": "<string: material if visible e.g. قماش مقاوم للماء / Water-resistant Fabric>",\n'
        '  "visual_features": ["<feature 1>", "<feature 2>"],\n'
        '  "arabic_summary": "<string: 1 short sentence in Egyptian Arabic summarizing what the item is and its color>"\n'
        "}"
    )

    contents_parts = [{'text': prompt}] + image_parts
    payload = {
        "contents": [{"parts": contents_parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1,
            "maxOutputTokens": 800
        }
    }

    models_to_try = ['gemini-flash-lite-latest', 'gemini-flash-latest']
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-goog-api-key': api_key
                }
            )
            with urllib.request.urlopen(req, timeout=16) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                if '```json' in raw_text:
                    raw_text = raw_text.split('```json')[1].split('```')[0].strip()
                elif '```' in raw_text:
                    raw_text = raw_text.split('```')[1].split('```')[0].strip()
                    
                vision_data = json.loads(raw_text)
                
                # Auto-save/update ProductSpec records
                if vision_data.get('primary_color'):
                    ProductSpec.objects.update_or_create(
                        product=product,
                        name='Color',
                        defaults={'value': vision_data['primary_color'], 'icon': '🎨'}
                    )
                if vision_data.get('material'):
                    ProductSpec.objects.update_or_create(
                        product=product,
                        name='Material',
                        defaults={'value': vision_data['material'], 'icon': '🧵'}
                    )
                if vision_data.get('item_type'):
                    ProductSpec.objects.update_or_create(
                        product=product,
                        name='Type',
                        defaults={'value': vision_data['item_type'], 'icon': '📦'}
                    )
                    
                # Append visual summary to description if short
                if vision_data.get('arabic_summary') and (not product.description or len(product.description) < 40):
                    product.description = f"{product.description} {vision_data['arabic_summary']}".strip()
                    product.save(update_fields=['description'])
                    
                return {"success": True, "data": vision_data, "is_ai": True}
        except Exception as e:
            print(f"[Vision Analysis Gemini {model_name} Error]: {e}")
            continue

    return {"success": False, "error": "Vision API could not process images"}
