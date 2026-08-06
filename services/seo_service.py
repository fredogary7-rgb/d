"""
TransAfrik SEO Service — Centralisation des métadonnées SEO
Domaine : https://transafrik.org
Logo : /static/img/trans1.png
Couleur thème : #2563EB
"""

import json
from datetime import datetime, date
from flask import url_for, request

# ── CONSTANTES GLOBALES ──
SITE_NAME = "TransAfrik"
SITE_DOMAIN = "https://transafrik.org"
SITE_LOGO = f"{SITE_DOMAIN}/static/img/trans1.png"
SITE_THEME_COLOR = "#2563EB"
SITE_BG_COLOR = "#FFFFFF"
SITE_DESCRIPTION = (
    "TransAfrik — Transfert d'argent instantané en Afrique. "
    "Envoyez et recevez de l'argent au Togo, Bénin, Cameroun, Côte d'Ivoire, Burkina Faso, Congo, Gabon, Sénégal et plus. "
    "Service rapide, sécurisé et accessible 24/7."
)
SITE_KEYWORDS = (
    "transfert argent Afrique, envoi argent Togo, mobile money, "
    "TransAfrik, paiement mobile, transfert international Afrique, "
    "envoyer argent Bénin, Cameroun, Côte d'Ivoire, transfert instantané"
)
SITE_AUTHOR = "TransAfrik"
SITE_TWITTER_HANDLE = "@TransAfrik"

# ── METADATA PAR PAGE ──
PAGE_META = {
    "/": {
        "title": "TransAfrik — Transfert d'argent instantané en Afrique | Accueil",
        "description": SITE_DESCRIPTION,
        "keywords": SITE_KEYWORDS,
        "canonical": "/",
        "priority": 1.0,
        "changefreq": "daily",
        "og_type": "website",
    },
    "/about": {
        "title": "À propos de TransAfrik — Notre mission et notre équipe",
        "description": "Découvrez TransAfrik, la plateforme de transfert d'argent rapide et sécurisée pour l'Afrique. Notre mission : rendre les transferts accessibles à tous.",
        "keywords": "à propos TransAfrik, mission, équipe, transfert argent Afrique",
        "canonical": "/about",
        "priority": 0.7,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/contact": {
        "title": "Contactez TransAfrik — Support client 24/7",
        "description": "Besoin d'aide ? Contactez l'équipe TransAfrik. Support client disponible 24h/24 et 7j/7 par email, téléphone et chat.",
        "keywords": "contact TransAfrik, support, aide, assistance transfert",
        "canonical": "/contact",
        "priority": 0.8,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/faq": {
        "title": "FAQ — Questions fréquentes sur TransAfrik",
        "description": "Trouvez les réponses à vos questions sur les transferts, les frais, les délais et la sécurité chez TransAfrik.",
        "keywords": "FAQ TransAfrik, questions fréquentes, aide transfert, frais",
        "canonical": "/faq",
        "priority": 0.6,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/privacy": {
        "title": "Politique de confidentialité — TransAfrik",
        "description": "Consultez la politique de confidentialité de TransAfrik. Vos données personnelles sont protégées et sécurisées.",
        "keywords": "confidentialité TransAfrik, données personnelles, sécurité",
        "canonical": "/privacy",
        "priority": 0.4,
        "changefreq": "yearly",
        "og_type": "website",
    },
    "/terms": {
        "title": "Conditions générales d'utilisation — TransAfrik",
        "description": "Lisez les conditions générales d'utilisation de TransAfrik. Utilisation des services, droits et obligations.",
        "keywords": "conditions TransAfrik, CGU, conditions utilisation",
        "canonical": "/terms",
        "priority": 0.4,
        "changefreq": "yearly",
        "og_type": "website",
    },
    "/login": {
        "title": "Connexion — TransAfrik",
        "description": "Connectez-vous à votre compte TransAfrik pour envoyer et recevoir de l'argent en toute sécurité.",
        "keywords": "connexion TransAfrik, login, accès compte",
        "canonical": "/login",
        "priority": 0.8,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/register": {
        "title": "Inscription — Créez votre compte TransAfrik gratuitement",
        "description": "Inscrivez-vous sur TransAfrik et commencez à envoyer de l'argent en Afrique. Création de compte gratuite en 2 minutes.",
        "keywords": "inscription TransAfrik, créer compte, ouvrir compte, register",
        "canonical": "/register",
        "priority": 0.9,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/send-money": {
        "title": "Envoyer de l'argent — TransAfrik",
        "description": "Envoyez de l'argent instantanément vers l'Afrique. Transfert mobile money, virement bancaire. Frais réduits, délai immédiat.",
        "keywords": "envoyer argent, transfert mobile money, envoi Afrique",
        "canonical": "/send-money",
        "priority": 0.9,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/scan-qr": {
        "title": "Scanner un QR Code — TransAfrik",
        "description": "Scannez un QR code pour payer ou recevoir de l'argent instantanément avec TransAfrik.",
        "keywords": "QR code, scanner, paiement mobile, scan TransAfrik",
        "canonical": "/scan-qr",
        "priority": 0.8,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/features": {
        "title": "Fonctionnalités — TransAfrik",
        "description": "Découvrez toutes les fonctionnalités de TransAfrik : transferts, paiements, QR code, portefeuille, historique, bénéficiaires.",
        "keywords": "fonctionnalités TransAfrik, services, transfert, paiement",
        "canonical": "/features",
        "priority": 0.7,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/services": {
        "title": "Nos services — TransAfrik",
        "description": "TransAfrik propose des services de transfert d'argent, paiement mobile, rechargement, conversion de devises.",
        "keywords": "services TransAfrik, transfert, paiement, mobile money",
        "canonical": "/services",
        "priority": 0.7,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/security": {
        "title": "Sécurité — TransAfrik",
        "description": "La sécurité est notre priorité. Découvrez comment TransAfrik protège vos transactions et vos données personnelles.",
        "keywords": "sécurité TransAfrik, protection données, transactions sécurisées",
        "canonical": "/security",
        "priority": 0.7,
        "changefreq": "monthly",
        "og_type": "website",
    },
    "/support": {
        "title": "Support — TransAfrik",
        "description": "Besoin d'aide ? Contactez le support TransAfrik. Assistance par email, téléphone et chat disponible 24/7.",
        "keywords": "support TransAfrik, aide, assistance, contact",
        "canonical": "/support",
        "priority": 0.8,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/fees-calculator": {
        "title": "Calculateur de frais — TransAfrik",
        "description": "Calculez les frais de transfert avant d'envoyer de l'argent avec TransAfrik. Simulateur gratuit et transparent.",
        "keywords": "calculateur frais, simulateur, frais transfert, TransAfrik",
        "canonical": "/fees-calculator",
        "priority": 0.7,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/scan": {
        "title": "Scanner — TransAfrik",
        "description": "Scannez un QR code TransAfrik pour effectuer un paiement ou recevoir de l'argent.",
        "keywords": "scan, QR code, scanner TransAfrik",
        "canonical": "/scan",
        "priority": 0.7,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/converter": {
        "title": "Convertisseur de devises — TransAfrik",
        "description": "Convertissez vos devises en temps réel. Convertisseur intégré pour les transferts TransAfrik.",
        "keywords": "convertisseur, devises, taux de change, conversion, TransAfrik",
        "canonical": "/converter",
        "priority": 0.6,
        "changefreq": "weekly",
        "og_type": "website",
    },
    "/forgot-password": {
        "title": "Mot de passe oublié — TransAfrik",
        "description": "Réinitialisez votre mot de passe TransAfrik en quelques étapes simples et sécurisées.",
        "keywords": "mot de passe oublié, réinitialisation, TransAfrik",
        "canonical": "/forgot-password",
        "priority": 0.3,
        "changefreq": "yearly",
        "og_type": "website",
    },
}

# ── ROUTES PUBLIQUES POUR LE SITEMAP ──
SITEMAP_ROUTES = [
    ("/", "daily", 1.0),
    ("/about", "monthly", 0.7),
    ("/contact", "monthly", 0.8),
    ("/faq", "monthly", 0.6),
    ("/privacy", "yearly", 0.4),
    ("/terms", "yearly", 0.4),
    ("/login", "weekly", 0.8),
    ("/register", "weekly", 0.9),
    ("/send-money", "weekly", 0.9),
    ("/scan-qr", "weekly", 0.8),
    ("/features", "monthly", 0.7),
    ("/services", "monthly", 0.7),
    ("/security", "monthly", 0.7),
    ("/support", "weekly", 0.8),
    ("/fees-calculator", "weekly", 0.7),
    ("/scan", "weekly", 0.7),
    ("/converter", "weekly", 0.6),
    ("/forgot-password", "yearly", 0.3),
]


# ══════════════════════════════════════════════════════════════
#  HELPER : Générer les metadata pour une page donnée
# ══════════════════════════════════════════════════════════════

def get_page_meta(path):
    """Retourne les métadonnées SEO pour le chemin donné."""
    # Nettoyer le chemin
    clean_path = "/" + path.lstrip("/") if path else "/"

    # Chercher une correspondance exacte
    if clean_path in PAGE_META:
        return PAGE_META[clean_path]

    # Chercher une correspondance partielle (pour les routes dynamiques)
    for route, meta in PAGE_META.items():
        if route != "/" and clean_path.startswith(route.rstrip("/")):
            return meta

    # Default
    return {
        "title": "TransAfrik — Transfert d'argent en Afrique",
        "description": SITE_DESCRIPTION,
        "keywords": SITE_KEYWORDS,
        "canonical": clean_path,
        "priority": 0.5,
        "changefreq": "weekly",
        "og_type": "website",
    }


def get_default_meta():
    """Métadonnées par défaut."""
    return {
        "title": "TransAfrik — Transfert d'argent en Afrique",
        "description": SITE_DESCRIPTION,
        "keywords": SITE_KEYWORDS,
        "author": SITE_AUTHOR,
        "canonical": "/",
        "site_name": SITE_NAME,
        "url": SITE_DOMAIN,
        "logo": SITE_LOGO,
        "theme_color": SITE_THEME_COLOR,
        "bg_color": SITE_BG_COLOR,
        "og_type": "website",
        "twitter_card": "summary_large_image",
        "twitter_handle": SITE_TWITTER_HANDLE,
        "locale": "fr_FR",
        "robots": "index, follow",
    }


# ══════════════════════════════════════════════════════════════
#  JSON-LD Structured Data
# ══════════════════════════════════════════════════════════════

def get_organization_ld():
    """Schema.org Organization pour TransAfrik."""
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": SITE_NAME,
        "url": SITE_DOMAIN,
        "logo": SITE_LOGO,
        "description": SITE_DESCRIPTION,
        "email": "support@transafrik.org",
        "sameAs": [
            f"{SITE_DOMAIN}",
        ],
        "contactPoint": {
            "@type": "ContactPoint",
            "contactType": "customer service",
            "availableLanguage": ["fr", "en"],
        },
    }


def get_financial_service_ld():
    """Schema.org FinancialService."""
    return {
        "@context": "https://schema.org",
        "@type": "FinancialService",
        "name": SITE_NAME,
        "url": SITE_DOMAIN,
        "description": SITE_DESCRIPTION,
        "provider": {
            "@type": "Organization",
            "name": SITE_NAME,
        },
    }


def get_website_ld():
    """Schema.org WebSite avec SearchAction."""
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": SITE_DOMAIN,
        "description": SITE_DESCRIPTION,
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{SITE_DOMAIN}/search?q={{search_term_string}}",
            },
            "query-input": "required name=search_term_string",
        },
    }


def get_breadcrumb_ld(items):
    """Schema.org BreadcrumbList."""
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": idx + 1,
                "name": item["name"],
                "item": item.get("url", "#"),
            }
            for idx, item in enumerate(items)
        ],
    }


def get_all_structured_data():
    """Retourne toutes les données structurées."""
    org = get_organization_ld()
    fin = get_financial_service_ld()
    web = get_website_ld()
    return [org, fin, web]


# ══════════════════════════════════════════════════════════════
#  Sitemap XML
# ══════════════════════════════════════════════════════════════

def generate_sitemap_xml():
    """Génère le contenu XML du sitemap."""
    today = date.today().isoformat()
    urls = []

    for route, changefreq, priority in SITEMAP_ROUTES:
        urls.append(f"""  <url>
    <loc>{SITE_DOMAIN}{route}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""
    return xml


# ══════════════════════════════════════════════════════════════
#  Robots.txt
# ══════════════════════════════════════════════════════════════

ROBOTS_TXT = f"""User-agent: *
Allow: /

Disallow: /admin/
Disallow: /dashboard/
Disallow: /api/
Disallow: /webhook/
Disallow: /wallet/
Disallow: /profile/
Disallow: /notifications/
Disallow: /logout
Disallow: /transfer/
Disallow: /deposit/
Disallow: /withdraw/
Disallow: /history/
Disallow: /settings/
Disallow: /support/ticket/
Disallow: /beneficiaries/
Disallow: /verify-otp/
Disallow: /kyc/
Disallow: /receive/
Disallow: /request/
Disallow: /pay/
Disallow: /reset-password/

Sitemap: {SITE_DOMAIN}/sitemap.xml
"""


# ══════════════════════════════════════════════════════════════
#  Helper pour template context processor
# ══════════════════════════════════════════════════════════════

def get_seo_context(path=None, title_override=None, description_override=None, canonical_override=None):
    """Retourne le contexte SEO complet à injecter dans les templates."""
    if path is None:
        path = request.path if request else "/"

    meta = get_page_meta(path)
    defaults = get_default_meta()

    result = {
        # Title
        "seo_title": title_override or meta.get("title", defaults["title"]),
        # Description
        "seo_description": description_override or meta.get("description", defaults["description"]),
        # Keywords
        "seo_keywords": meta.get("keywords", defaults["keywords"]),
        # Canonical
        "seo_canonical": canonical_override or SITE_DOMAIN + meta.get("canonical", path),
        # Author
        "seo_author": defaults["author"],
        # Open Graph
        "seo_og_title": title_override or meta.get("title", defaults["title"]),
        "seo_og_description": description_override or meta.get("description", defaults["description"]),
        "seo_og_image": defaults["logo"],
        "seo_og_url": SITE_DOMAIN + meta.get("canonical", path),
        "seo_og_type": meta.get("og_type", defaults["og_type"]),
        "seo_og_site_name": defaults["site_name"],
        "seo_og_locale": defaults["locale"],
        # Twitter
        "seo_twitter_card": defaults["twitter_card"],
        "seo_twitter_title": title_override or meta.get("title", defaults["title"]),
        "seo_twitter_description": description_override or meta.get("description", defaults["description"]),
        "seo_twitter_image": defaults["logo"],
        "seo_twitter_handle": defaults["twitter_handle"],
        # Robots
        "seo_robots": defaults["robots"],
        # Structured Data
        "seo_structured_data": json.dumps(get_all_structured_data(), ensure_ascii=False),
        # Global
        "seo_site_name": defaults["site_name"],
        "seo_site_domain": SITE_DOMAIN,
        "seo_logo": defaults["logo"],
        "seo_theme_color": SITE_THEME_COLOR,
        "seo_bg_color": defaults["bg_color"],
    }

    return result