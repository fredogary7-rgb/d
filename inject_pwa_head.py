"""
Injecte {% include "_pwa_head.html" %} dans tous les templates HTML
qui ont une balise <meta name="viewport"> mais pas encore l'include.
"""
import os
import re

templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
skip_files = ['_pwa_head.html', 'offline.html']

updated = []
already = []
not_found = []

for filename in sorted(os.listdir(templates_dir)):
    if not filename.endswith('.html'):
        continue
    if filename in skip_files:
        continue
    
    filepath = os.path.join(templates_dir, filename)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '{% include "_pwa_head.html" %}' in content:
        already.append(filename)
        continue
    
    # Insert after viewport meta tag
    pattern = r'(<meta\s+name="viewport"[^>]*>\s*\n)'
    replacement = r'\1    {% include "_pwa_head.html" %}\n'
    
    new_content = re.sub(pattern, replacement, content, count=1)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        updated.append(filename)
    else:
        not_found.append(filename)

print(f'Mise a jour : {len(updated)} fichiers')
for f in updated:
    print(f'  + {f}')
print(f'Deja fait : {len(already)}')
for f in already:
    print(f'  = {f}')
if not_found:
    print(f'Pattern non trouve : {len(not_found)}')
    for f in not_found:
        print(f'  ? {f}')