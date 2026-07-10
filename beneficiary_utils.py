"""Utilitaires pour la gestion des bénéficiaires."""

from datetime import datetime


# Préfixes téléphoniques par pays (Afrique subsaharienne)
PHONE_PREFIX_MAP = {
    '228': 'TG',  # Togo
    '229': 'BJ',  # Bénin
    '237': 'CM',  # Cameroun
    '225': 'CI',  # Côte d'Ivoire
    '226': 'BF',  # Burkina Faso
    '242': 'CG',  # Congo Brazzaville
    '243': 'CD',  # RD Congo
    '241': 'GA',  # Gabon
    '256': 'UG',  # Ouganda
    '260': 'ZM',  # Zambie
    '221': 'SN',  # Sénégal
}

# Détection opérateur par préfixe local (après code pays) — (préfixe, opérateur_slug, pays)
# Format : (préfixe_sans_code_pays, operator_slug, country_code, operator_name)
OPERATOR_PREFIX_DETECTION = {
    # Togo +228
    '90': ('tmoney', 'TG', 'TMoney'),
    '91': ('tmoney', 'TG', 'TMoney'),
    '92': ('tmoney', 'TG', 'TMoney'),
    '93': ('tmoney', 'TG', 'TMoney'),
    '79': ('moov', 'TG', 'Moov Money'),
    '70': ('moov', 'TG', 'Moov Money'),
    '71': ('moov', 'TG', 'Moov Money'),
    # Bénin +229
    '60': ('moov', 'BJ', 'Moov Money'),
    '61': ('moov', 'BJ', 'Moov Money'),
    '62': ('moov', 'BJ', 'Moov Money'),
    '90': ('mtn', 'BJ', 'MTN MoMo'),
    '91': ('mtn', 'BJ', 'MTN MoMo'),
    '97': ('mtn', 'BJ', 'MTN MoMo'),
    # Cameroun +237
    '69': ('orange', 'CM', 'Orange Money'),
    '68': ('mtn', 'CM', 'MTN MoMo'),
    '67': ('mtn', 'CM', 'MTN MoMo'),
    '66': ('mtn', 'CM', 'MTN MoMo'),
    # Côte d'Ivoire +225
    '07': ('orange', 'CI', 'Orange Money'),
    '05': ('mtn', 'CI', 'MTN MoMo'),
    '01': ('moov', 'CI', 'Moov Money'),
    # Burkina Faso +226
    '70': ('moov', 'BF', 'Moov Money'),
    '71': ('moov', 'BF', 'Moov Money'),
    '64': ('orange', 'BF', 'Orange Money'),
    '65': ('orange', 'BF', 'Orange Money'),
    # Congo +242
    '06': ('mtn', 'CG', 'MTN MoMo'),
    '05': ('airtel', 'CG', 'Airtel Money'),
    # RD Congo +243
    '97': ('orange', 'CD', 'Orange Money'),
    '89': ('orange', 'CD', 'Orange Money'),
    '82': ('vodacom', 'CD', 'Vodacom M-Pesa'),
    '81': ('vodacom', 'CD', 'Vodacom M-Pesa'),
    '99': ('airtel', 'CD', 'Airtel Money'),
    # Gabon +241
    '07': ('airtel', 'GA', 'Airtel Money'),
    # Ouganda +256
    '78': ('mtn', 'UG', 'MTN MoMo'),
    '77': ('mtn', 'UG', 'MTN MoMo'),
    '75': ('airtel', 'UG', 'Airtel Money'),
    # Zambie +260
    '97': ('airtel', 'ZM', 'Airtel Money'),
    '96': ('mtn', 'ZM', 'MTN MoMo'),
    '95': ('zamtel', 'ZM', 'Zamtel Money'),
    # Sénégal +221
    '78': ('orange', 'SN', 'Orange Money'),
    '77': ('orange', 'SN', 'Orange Money'),
    '76': ('free', 'SN', 'Free Money'),
    '70': ('expresso', 'SN', 'Expresso'),
    # Wave (Sénégal spécifique)
    '75': ('wave', 'SN', 'Wave'),
}


def format_phone_display(phone: str) -> str:
    """Formate un numéro de téléphone pour l'affichage."""
    if not phone:
        return ''
    clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    if len(clean) <= 4:
        return clean
    return f'•••• {clean[-4:]}'


def get_avatar_initials(name: str) -> str:
    """Retourne les initiales pour l'avatar (2 caractères max)."""
    if not name:
        return '?'
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()


def get_operator_color(operator: str) -> str:
    """Retourne la classe CSS de couleur pour un opérateur."""
    mapping = {
        'TMONEY': '#FFB300',
        'MOOV': '#006699',
        'MTN': '#FFCC00',
        'ORANGE': '#FF6600',
        'WAVE': '#0055CC',
        'AIRTEL': '#EE0000',
        'VODACOM': '#E60000',
        'FREE': '#E91E63',
        'WIZALL': '#9C27B0',
        'ZAMTEL': '#4CAF50',
    }
    return mapping.get(operator.upper(), '#64748B')


def detect_country_from_phone(phone: str) -> str:
    """Détecte le code pays à partir d'un numéro de téléphone (préfixe international).
    Ex: '+22890123456' → 'TG', '22890123456' → 'TG', '070123456' (local) → 'TG' si déjà en variable.
    Retourne '' si non détecté.
    """
    if not phone:
        return ''
    clean = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    clean = clean.lstrip('0')  # enlever les 0 initiaux
    for prefix, country in sorted(PHONE_PREFIX_MAP.items(), key=lambda x: -len(x[0])):
        if clean.startswith(prefix):
            return country
    return ''


def detect_operator_from_phone(phone: str, country_code: str = '') -> dict | None:
    """Détecte l'opérateur à partir du numéro et du pays.
    Ex: '+22890123456' → {'slug': 'tmoney', 'name': 'TMoney', 'country': 'TG'}
    Retourne None si non détecté.
    """
    if not phone:
        return None
    clean = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

    # Déterminer le pays si pas fourni
    country = country_code.upper().strip() if country_code else detect_country_from_phone(phone)
    if not country:
        return None

    # Retirer le préfixe pays du numéro
    country_prefix = None
    for prefix, cc in PHONE_PREFIX_MAP.items():
        if cc == country:
            country_prefix = prefix
            break

    if country_prefix and clean.startswith(country_prefix):
        local = clean[len(country_prefix):]
    else:
        local = clean.lstrip('0')

    # Chercher le préfixe local (2 chiffres)
    for length in (2, 3):
        prefix_key = local[:length]
        detection = OPERATOR_PREFIX_DETECTION.get(prefix_key)
        if detection and detection[2] == country:
            return {
                'slug': detection[0],
                'name': detection[2],
                'country': detection[1],
            }

    return None


def detect_from_phone(phone: str) -> dict:
    """Détecte le pays ET l'opérateur depuis un numéro.
    Retourne {'country': str, 'operator_name': str, 'operator_slug': str}
    """
    if not phone:
        return {'country': '', 'operator_name': '', 'operator_slug': ''}

    country = detect_country_from_phone(phone)
    op = detect_operator_from_phone(phone, country)

    return {
        'country': country or '',
        'operator_name': op['name'] if op else '',
        'operator_slug': op['slug'] if op else '',
    }