import os
import re

def fix_admin_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace unfold leftover in shop/admin.py
    content = content.replace('from unfold.admin import TabularInline', 'from django.contrib.admin import TabularInline')
    
    # Replace boolean=True with no boolean flag for string status methods
    content = re.sub(r'@admin\.display\((description=.*?),\s*boolean=True\)', r'@admin.display(\1)', content)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed {path}')

for root, _, files in os.walk('.'):
    for file in files:
        if file == 'admin.py':
            fix_admin_file(os.path.join(root, file))
