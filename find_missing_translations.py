import os
import re

def check_html_files(directory):
    for root, dirs, files in os.walk(directory):
        if 'venv' in root or '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    parts = re.split(r'\{%.*?%\}|\{\{.*?\}\}', content)
                    
                    for part in parts:
                        texts = re.findall(r'>([^<]+)<', part)
                        for t in texts:
                            clean_t = t.strip()
                            if clean_t and re.search(r'[a-zA-Z]', clean_t):
                                # Skip CSS
                                if 'keyframes' in clean_t or '{' in clean_t or 'font-family' in clean_t:
                                    continue
                                try:
                                    print(f"File: {path} -> '{clean_t}'")
                                except UnicodeEncodeError:
                                    pass

check_html_files('.')
