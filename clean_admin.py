import os
import re

def clean_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex to match @display(description="...", label={...})
    # We replace it with @admin.display(description="...", boolean=True)
    new_content = re.sub(
        r'@display\(\s*description=(\".*?\"),\s*label=\{[^\}]+\}\s*\)', 
        r'@admin.display(description=\1, boolean=True)', 
        content, 
        flags=re.DOTALL
    )
    
    # Catch any remaining @display
    new_content = new_content.replace('@display(', '@admin.display(')

    # Remove the manual display import we added earlier
    new_content = new_content.replace('from django.contrib.admin import display\n', '')
    new_content = new_content.replace('from django.contrib.admin import ModelAdmin, display\n', 'from django.contrib.admin import ModelAdmin\n')

    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {path}')

for root, _, files in os.walk('.'):
    for file in files:
        if file == 'admin.py':
            clean_file(os.path.join(root, file))
