"""
Configuration des pays et opérateurs pour les transferts TransAfrik.

Format facilement modifiable.
Chaque pays a :
  - name : nom affiché
  - flag : emoji drapeau
  - currency : devise locale (optionnelle, défaut XOF)
  - operators : liste des operateurs disponibles
"""

COUNTRIES = [
    {
        "code": "TG",
        "name": "Togo",
        "flag": "🇹🇬",
        "currency": "XOF",
        "operators": [
            {"id": "tmoney", "name": "TMoney"},
            {"id": "moov", "name": "Moov Money"},
        ],
    },
    {
        "code": "BJ",
        "name": "Bénin",
        "flag": "🇧🇯",
        "currency": "XOF",
        "operators": [
            {"id": "mtn", "name": "MTN MoMo"},
            {"id": "moov", "name": "Moov Money"},
        ],
    },
    {
        "code": "CI",
        "name": "Côte d'Ivoire",
        "flag": "🇨🇮",
        "currency": "XOF",
        "operators": [
            {"id": "orange", "name": "Orange Money"},
            {"id": "mtn", "name": "MTN MoMo"},
            {"id": "wave", "name": "Wave"},
            {"id": "moov", "name": "Moov Money"},
        ],
    },
    {
        "code": "CM",
        "name": "Cameroun",
        "flag": "🇨🇲",
        "currency": "XAF",
        "operators": [
            {"id": "orange", "name": "Orange Money"},
            {"id": "mtn", "name": "MTN MoMo"},
        ],
    },
    {
        "code": "CD",
        "name": "RD Congo",
        "flag": "🇨🇩",
        "currency": "CDF",
        "operators": [
            {"id": "orange", "name": "Orange Money"},
            {"id": "airtel", "name": "Airtel Money"},
            {"id": "vodacom", "name": "M-Pesa (Vodacom)"},
        ],
    },
    {
        "code": "BF",
        "name": "Burkina Faso",
        "flag": "🇧🇫",
        "currency": "XOF",
        "operators": [
            {"id": "orange", "name": "Orange Money"},
            {"id": "moov", "name": "Moov Money"},
        ],
    },
    {
        "code": "SN",
        "name": "Sénégal",
        "flag": "🇸🇳",
        "currency": "XOF",
        "operators": [
            {"id": "orange", "name": "Orange Money"},
            {"id": "free", "name": "Free Money"},
            {"id": "wave", "name": "Wave"},
        ],
    },
    {
        "code": "GA",
        "name": "Gabon",
        "flag": "🇬🇦",
        "currency": "XAF",
        "operators": [
            {"id": "airtel", "name": "Airtel Money"},
            {"id": "moov", "name": "Moov Money"},
        ],
    },
    {
        "code": "CG",
        "name": "Congo",
        "flag": "🇨🇬",
        "currency": "XAF",
        "operators": [
            {"id": "airtel", "name": "Airtel Money"},
            {"id": "mtn", "name": "MTN MoMo"},
        ],
    },
    {
        "code": "UG",
        "name": "Ouganda",
        "flag": "🇺🇬",
        "currency": "UGX",
        "operators": [
            {"id": "mtn", "name": "MTN MoMo"},
            {"id": "airtel", "name": "Airtel Money"},
        ],
    },
    {
        "code": "ZM",
        "name": "Zambie",
        "flag": "🇿🇲",
        "currency": "ZMW",
        "operators": [
            {"id": "mtn", "name": "MTN MoMo"},
            {"id": "airtel", "name": "Airtel Money"},
            {"id": "zamtel", "name": "Zamtel Money"},
        ],
    },
]

# Import aussi depuis les pays supportés par le dashboard
COUNTRY_FLAGS = {c["code"]: c["flag"] for c in COUNTRIES}
COUNTRY_NAMES = {c["code"]: c["name"] for c in COUNTRIES}
COUNTRY_CURRENCIES = {c["code"]: c["currency"] for c in COUNTRIES}


def get_operators(country_code: str):
    """Retourne la liste des opérateurs pour un pays donné."""
    for country in COUNTRIES:
        if country["code"] == country_code:
            return country["operators"]
    return []


def get_country(country_code: str):
    """Retourne le dictionnaire complet d'un pays."""
    for country in COUNTRIES:
        if country["code"] == country_code:
            return country
    return None