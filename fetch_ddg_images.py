import json
import re
import urllib.request
import urllib.parse

def search_ddg_images(query):
    # Step 1: get vqd
    url = 'https://duckduckgo.com/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    vqd_match = re.search(r'vqd=([\d-]+)', html)
    if not vqd_match: 
        # try another regex
        vqd_match = re.search(r'vqd=\"([^\"]+)\"', html)
        if not vqd_match: return []
    vqd = vqd_match.group(1)
    
    # Step 2: search images
    search_url = f"https://duckduckgo.com/i.js?q={urllib.parse.quote(query)}&o=json&vqd={vqd}"
    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    res = urllib.request.urlopen(req).read().decode('utf-8')
    data = json.loads(res)
    return [r['image'] for r in data.get('results', [])]

urls = search_ddg_images("technology black and white wallpaper 1920x1080")
for u in urls[:4]:
    print(u)
