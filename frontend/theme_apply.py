import os
import re

css_token_map = {
    'var(--bg)': 'var(--color-ink)',
    'var(--bg-color)': 'var(--color-ink)',
    'var(--surface)': 'var(--color-surface)',
    'var(--surface-color)': 'var(--color-surface)',
    'var(--surface-hover)': 'var(--color-surface-2)',
    'var(--border)': 'var(--color-edge)',
    'var(--border-color)': 'var(--color-edge)',
    'var(--border-light)': 'var(--color-edge-2)',
    'var(--primary)': 'var(--color-blue)',
    'var(--primary-hover)': 'var(--color-blue-dark)',
    'var(--text)': 'var(--color-white)',
    'var(--text-color)': 'var(--color-white)',
    'var(--text-secondary)': 'var(--color-mist)',
    'var(--text-muted)': 'var(--color-slate)',
    'var(--success)': 'var(--color-green)',
    'var(--warning)': 'var(--color-amber)',
    'var(--danger)': 'var(--color-red)',
    'var(--info)': 'var(--color-blue)',
}

def apply_replacements(content):
    for old, new in css_token_map.items():
        content = content.replace(old, new)
    return content

src_dir = r"c:\Users\Aditya\Desktop\NYU Academics\Spring Sem\Inventory Management System\frontend\src"

for root, dirs, files in os.walk(src_dir):
    for file in files:
        if file.endswith('.css') or file.endswith('.tsx'):
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = apply_replacements(content)
            
            if new_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {file_path}")

print("Token replacement complete.")
