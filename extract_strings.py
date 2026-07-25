import os
import re

strings = set()
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.html'):
            with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                content = f.read()
                matches = re.findall(r'\{% trans "(.*?)" %\}', content)
                for m in matches:
                    strings.add(m)

print("FOUND STRINGS:")
for s in sorted(strings):
    print(f'"{s}"')
