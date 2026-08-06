#!/usr/bin/env python
"""
TransAfrik — Générateur d'icônes PWA
=====================================
À partir de static/img/trans1.png, génère :
  - Toutes les icônes pour le manifest (72x72 → 512x512)
  - Maskable icons
  - Apple touch icons
  - Favicons (16x16, 32x32, favicon.ico)
  - Splash screens iOS

Prérequis : pip install Pillow
Usage : python generate_pwa_icons.py
"""
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ Pillow non installé. Lancez : pip install Pillow")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / 'static'
LOGO_PATH = STATIC_DIR / 'img/trans1.png'
ICONS_DIR = STATIC_DIR / 'img' / 'icons'
SPLASH_DIR = STATIC_DIR / 'img' / 'splash'
FAVICON_PATH = STATIC_DIR / 'favicon.ico'

# Couleurs officielles TransAfrik
BG_COLOR = (11, 17, 32)      # #0B1120 — Fond sombre
BRAND_BLUE = (37, 99, 235)   # #2563EB — Bleu TransAfrik
WHITE = (255, 255, 255)

def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)

def create_icon(size, output_path, is_maskable=False):
    """Génère une icône carrée avec le logo centré."""
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert('RGBA')
    else:
        # Fallback : créer un logo textuel
        logo = create_text_logo(size)

    # Pour les maskable, ajouter un padding de sécurité (80% de la taille)
    if is_maskable:
        safe_size = int(size * 0.8)
        safe_area_size = int(size * 0.625)
    else:
        safe_size = size
        safe_area_size = 0

    # Créer le canvas
    icon = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    # Fond gradient ou solide
    draw = ImageDraw.Draw(icon)
    if BG_COLOR:
        for y in range(size):
            ratio = y / size
            r = int(BG_COLOR[0] * (1 - ratio * 0.3))
            g = int(BG_COLOR[1] * (1 - ratio * 0.3))
            b = int(BG_COLOR[2] * (1 - ratio * 0.3))
            draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    # Redimensionner le logo
    logo_size = safe_size if not is_maskable else int(size * 0.6)
    logo_resized = logo.resize((logo_size, logo_size), Image.LANCZOS)

    # Centrer
    x = (size - logo_resized.width) // 2
    y = (size - logo_resized.height) // 2
    icon.paste(logo_resized, (x, y), logo_resized if logo_resized.mode == 'RGBA' else None)

    # Enregistrer
    icon.save(output_path, 'PNG')
    print(f'  [OK] {output_path.name} ({size}x{size})')

def create_text_logo(size):
    """Crée un logo textuel de fallback 'TA'."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cercle de fond bleu
    circle_size = int(size * 0.75)
    circle_x = (size - circle_size) // 2
    circle_y = (size - circle_size) // 2
    draw.ellipse(
        [circle_x, circle_y, circle_x + circle_size, circle_y + circle_size],
        fill=BRAND_BLUE + (255,),
    )

    # Texte "TA"
    try:
        font_size = int(size * 0.35)
        font = ImageFont.truetype('arial.ttf', font_size)
    except:
        font = ImageFont.load_default()

    text = 'TA'
    bbox = draw.textbbox((0, 0), text, font=font) if hasattr(draw, 'textbbox') else None
    if bbox:
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    else:
        tw, th = draw.textsize(text, font=font)

    draw.text(
        ((size - tw) // 2, (size - th) // 2 - int(size * 0.02)),
        text,
        fill=WHITE,
        font=font,
    )
    return img

def create_splash_screen(width, height, output_path):
    """Génère un splash screen iOS."""
    img = Image.new('RGB', (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Dégradé subtil
    for y in range(height):
        ratio = y / height
        r = int(BG_COLOR[0] * (1 - ratio * 0.2))
        g = int(BG_COLOR[1] * (1 - ratio * 0.2))
        b = int(BG_COLOR[2] * (1 - ratio * 0.2))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Logo centré
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert('RGBA')
        logo_size = int(min(width, height) * 0.2)
        logo_resized = logo.resize((logo_size, logo_size), Image.LANCZOS)
        logo_x = (width - logo_size) // 2
        logo_y = (height - logo_size) // 2 - int(height * 0.05)
        # Fond blanc derrière le logo
        bg = Image.new('RGBA', (logo_size, logo_size), (255, 255, 255, 0))
        img_rgba = img.convert('RGBA')
        img_rgba.paste(bg, (logo_x, logo_y), bg)
        img_rgba.paste(logo_resized, (logo_x, logo_y), logo_resized)
        img = img_rgba.convert('RGB')

    # Texte "TransAfrik"
    try:
        font = ImageFont.truetype('arial.ttf', int(min(width, height) * 0.04))
    except:
        font = ImageFont.load_default()

    text = 'TransAfrik'
    bbox = draw.textbbox((0, 0), text, font=font) if hasattr(draw, 'textbbox') else (0, 0, 0, 0)
    tw = bbox[2] - bbox[0] if bbox else draw.textsize(text, font=font)[0]
    draw.text(
        ((width - tw) // 2, height // 2 + int(min(width, height) * 0.15)),
        text,
        fill=(200, 210, 220),
        font=font,
    )

    # Barre de chargement simulée
    bar_width = int(width * 0.3)
    bar_height = 3
    bar_x = (width - bar_width) // 2
    bar_y = height - int(height * 0.15)
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(30, 40, 60))
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_width * 0.4), bar_y + bar_height], fill=BRAND_BLUE)

    img.save(output_path, 'PNG')
    print(f'  [OK] Splash {output_path.name} ({width}x{height})')

def create_favicons():
    """Génère favicon 16x16, 32x32 et favicon.ico."""
    sizes = [16, 32]
    for size in sizes:
        path = ICONS_DIR / f'icon-{size}x{size}.png'
        if not path.exists():
            create_icon(size, path)

    # Créer favicon.ico (16x16 + 32x32)
    try:
        icon16 = Image.open(ICONS_DIR / 'icon-16x16.png').convert('RGBA')
        icon32 = Image.open(ICONS_DIR / 'icon-32x32.png').convert('RGBA')

        # Sauvegarder en .ico avec les deux tailles
        icon16.save(FAVICON_PATH, format='ICO', sizes=[(16, 16), (32, 32)])
        print(f'  [OK] favicon.ico (16x16 + 32x32)')
    except Exception as e:
        # Fallback : utiliser la 32x32 seule
        icon32 = Image.open(ICONS_DIR / 'icon-32x32.png').convert('RGBA')
        icon32.save(FAVICON_PATH, format='ICO')
        print(f'  ⚠️ favicon.ico (32x32 uniquement) — {e}')

def generate_all():
    print('=' * 60)
    print('[ICON] TransAfrik — Générateur d\'icônes PWA')
    print('=' * 60)

    ensure_dir(ICONS_DIR)
    ensure_dir(SPLASH_DIR)

    if not LOGO_PATH.exists():
        print(f'⚠️  Logo non trouvé : {LOGO_PATH}')
        print('   Utilisation d\'un logo textuel de fallback (TA)...')
    else:
        print(f'📦 Logo source : {LOGO_PATH}')

    # Icônes Manifest
    print(f'\n📱 Génération des icônes PWA...')
    manifest_sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    for size in manifest_sizes:
        path = ICONS_DIR / f'icon-{size}x{size}.png'
        is_maskable = size in (192, 512)
        if not path.exists():
            create_icon(size, path, is_maskable=is_maskable)

    # Maskable icon séparée
    maskable_path = ICONS_DIR / 'maskable-512x512.png'
    if not maskable_path.exists():
        create_icon(512, maskable_path, is_maskable=True)

    # Shortcut icons
    for name in ['send', 'history', 'deposit']:
        shortcut_path = ICONS_DIR / f'{name}-96x96.png'
        if not shortcut_path.exists():
            create_icon(96, shortcut_path)

    # Favicons
    print(f'\n🖼️  Génération des favicons...')
    create_favicons()

    # Splash screens iOS
    print(f'\n[PHONE] Génération des splash screens iOS...')
    splash_sizes = [
        (1290, 2796, 'apple-splash-1290-2796.png'),   # iPhone 16 Pro Max
        (1179, 2556, 'apple-splash-1179-2556.png'),   # iPhone 16 Pro
        (1284, 2778, 'apple-splash-1284-2778.png'),   # iPhone 12/13 Pro Max
        (1170, 2532, 'apple-splash-1170-2532.png'),   # iPhone 12/13/14
        (1125, 2436, 'apple-splash-1125-2436.png'),   # iPhone X/XS/11 Pro
        (1242, 2688, 'apple-splash-1242-2688.png'),   # iPhone XS Max / 11 Pro Max
        (828, 1792, 'apple-splash-828-1792.png'),     # iPhone XR / 11
        (1242, 2208, 'apple-splash-1242-2208.png'),   # iPhone 6/7/8 Plus
        (750, 1334, 'apple-splash-750-1334.png'),     # iPhone 6/7/8/SE
        (2048, 2732, 'apple-splash-2048-2732.png'),   # iPad Pro 12.9"
        (1668, 2388, 'apple-splash-1668-2388.png'),   # iPad Pro 11"
        (1668, 2224, 'apple-splash-1668-2224.png'),   # iPad Pro 10.5"
        (1620, 2160, 'apple-splash-1620-2160.png'),   # iPad 10th gen
        (1536, 2048, 'apple-splash-1536-2048.png'),   # iPad Mini / Air
    ]
    for w, h, name in splash_sizes:
        path = SPLASH_DIR / name
        if not path.exists():
            create_splash_screen(w, h, path)

    # Browserconfig.xml pour Windows/Edge
    browserconfig_path = STATIC_DIR / 'browserconfig.xml'
    if not browserconfig_path.exists():
        browserconfig = '''<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
    <msapplication>
        <tile>
            <square70x70logo src="/static/img/icons/icon-72x72.png"/>
            <square150x150logo src="/static/img/icons/icon-152x152.png"/>
            <wide310x150logo src="/static/img/icons/icon-384x384.png"/>
            <square310x310logo src="/static/img/icons/icon-384x384.png"/>
            <TileColor>#0B1120</TileColor>
        </tile>
    </msapplication>
</browserconfig>'''
        browserconfig_path.write_text(browserconfig, encoding='utf-8')
        print(f'\n⚙️  Créé : browserconfig.xml')

    print(f'\n' + '=' * 60)
    print('[OK] Génération terminée avec succès !')
    print(f'📂 Icônes dans : {ICONS_DIR}')
    print(f'📂 Splashs dans : {SPLASH_DIR}')
    print(f'📂 Favicon  dans : {FAVICON_PATH}')
    print(f'\n🔗 Intégrez ceci dans chaque page HTML :')
    print(f'   {{% include "_pwa_head.html" %}}')
    print('=' * 60)

if __name__ == '__main__':
    generate_all()