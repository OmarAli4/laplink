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
    Extract a compact, token-efficient JSON list of available in-stock products with specs.
    """
    products = Product.objects.filter(available=True).select_related('category', 'brand').prefetch_related('specs')
    catalog = []
    for p in products:
        specs_dict = {s.name: s.value for s in p.specs.all()[:6]}
        catalog.append({
            "id": p.id,
            "name": p.name,
            "brand": p.brand.name if p.brand else "",
            "category": p.category.name if p.category else "",
            "price": float(p.current_price),
            "specs": specs_dict,
            "description": p.description[:120] if p.description else ""
        })
    return catalog


def ask_ai_tech_finder(user_prompt: str):
    """
    Pure Google Gemini LLM API Recommendation Engine.
    Directly analyzes user intent, use-case, and constraints using Gemini AI.
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
        "You are Lap Link AI Tech Finder, an elite tech store assistant in Egypt. "
        "A customer has asked: '" + user_prompt + "'.\n"
        "Here is our store's current in-stock product catalog:\n"
        f"{json.dumps(catalog, ensure_ascii=False)}\n\n"
        "Instructions:\n"
        "1. Analyze the customer's request carefully (intent, use-case, brand preference, budget, and single vs plural/all request).\n"
        "2. If the customer asks for a specific brand (e.g. Apple), ONLY return products of that brand strictly. Do NOT include other brands.\n"
        "3. If the customer asks for 'all laptops' or multiple options, return all matching product IDs in `product_ids`. If they ask for 1 specific laptop, return only that 1 product ID in `product_ids`.\n"
        "4. Reply in the EXACT same language and dialect as the customer (e.g. friendly Egyptian Arabic if Arabic, or English if English).\n"
        "5. Return ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "product_ids": [<list of matched integer product IDs meeting the criteria strictly, e.g. [2]>],\n'
        '  "product_id": <int: ID of the primary/best selected product>,\n'
        '  "match_score": <int: score 85-99>,\n'
        '  "ai_message": "<string: 2-3 friendly sentences in customer language explaining why these laptops were selected>",\n'
        '  "highlights": ["<string: key highlight 1>", "<string: key highlight 2>", "<string: key highlight 3>"]\n'
        "}"
    )

    models_to_try = ['gemini-flash-latest', 'gemini-flash-lite-latest', 'gemini-2.5-flash-lite']
    
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
                    parsed_data['product_ids'] = [parsed_data['product_id']]
                elif 'product_id' not in parsed_data and parsed_data.get('product_ids'):
                    parsed_data['product_id'] = parsed_data['product_ids'][0]
                    
                # Verify at least one product exists in our catalog
                valid_ids = [pid for pid in parsed_data.get('product_ids', []) if any(p['id'] == pid for p in catalog)]
                if valid_ids:
                    parsed_data['product_ids'] = valid_ids
                    parsed_data['product_id'] = valid_ids[0]
                    return {"success": True, "data": parsed_data, "is_ai": True}
        except Exception as e:
            last_error = e
            print(f"[AI Tech Finder Gemini {model_name} Error]: {e}")
            continue

    return {
        "success": False,
        "error": _(f"AI service temporarily unavailable: {last_error}")
    }
