"""
Render the battle template exactly as Django would and extract the x-data attribute.
"""
import os, sys, django, json, re
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myshop.settings')
os.environ['PYTHONIOENCODING'] = 'utf-8'
django.setup()

from django.test import RequestFactory
from shop.views import product_battle

# Create a fake request
factory = RequestFactory()
request = factory.get('/en/battle/')

# Set required attributes
from django.contrib.sessions.backends.db import SessionStore
request.session = SessionStore()
request.LANGUAGE_CODE = 'en'
request.user = type('AnonymousUser', (), {'is_authenticated': False})()

try:
    response = product_battle(request)
    html = response.content.decode('utf-8')
    
    # Save full HTML for inspection
    with open('debug_battle_output.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Full HTML saved to debug_battle_output.html ({len(html)} bytes)")
    
    # Extract the x-data attribute value
    # Find x-data="..." - need to handle nested quotes carefully
    xdata_start = html.find('x-data="')
    if xdata_start == -1:
        print("ERROR: x-data attribute not found!")
        sys.exit(1)
    
    xdata_start += len('x-data="')
    
    # Find the closing quote - count braces to find the right one
    depth = 0
    i = xdata_start
    in_string = False
    string_char = None
    escaped = False
    
    while i < len(html):
        ch = html[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if ch == '\\':
            escaped = True
            i += 1
            continue
        if in_string:
            if ch == string_char:
                in_string = False
        else:
            if ch == "'" or ch == '`':
                in_string = True
                string_char = ch
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    # Found the end of the x-data object
                    xdata_end = i + 1
                    break
            elif ch == '"' and depth == 0:
                # This would be the closing quote of the attribute
                xdata_end = i
                break
        i += 1
    
    xdata_value = html[xdata_start:xdata_end]
    
    print(f"\n=== x-data value ({len(xdata_value)} chars) ===")
    print(xdata_value[:500])
    print("...")
    print(xdata_value[-200:])
    
    # Check for obvious JS syntax issues
    print("\n=== Checking for potential issues ===")
    
    # Check unescaped single quotes inside single-quoted strings
    lines = xdata_value.split('\n')
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
            # Count single quotes
            sq_count = stripped.count("'")
            if sq_count % 2 != 0:
                print(f"  WARNING line {lineno}: Odd number of single quotes ({sq_count}): {stripped[:100]}")
    
except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    traceback.print_exc()
