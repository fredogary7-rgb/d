"""
Configuration centralisée de TOUS les opérateurs / services SoleasPay.

Format :
    OPERATORS[operator_key] = {
        "id": int,           # ID du service chez SoleasPay
        "country": str,      # Code pays ISO (CM, SN, CI, TG, etc.)
        "name": str,         # Nom commercial (Orange Money, MTN MoMo, etc.)
        "slug": str,         # Identifiant interne (orange, mtn, tmoney, etc.)
        "currency": str,     # Code devise principal
        "type": str,         # "mobile_money", "bank", "cash", "card", "currency"
        "active": bool,      # Actif chez SoleasPay
    }

Ne jamais hardcoder les IDs ailleurs. Toujours importer ce module.
"""

OPERATORS = {
    # =========================================================================
    # CAMEROUN
    # =========================================================================
    "MOMO CM": {
        "id": 1, "country": "CM", "name": "MTN MoMo",
        "slug": "mtn", "currency": "XAF", "type": "mobile_money", "active": True,
    },
    "OM CM": {
        "id": 2, "country": "CM", "name": "Orange Money",
        "slug": "orange", "currency": "XAF", "type": "mobile_money", "active": True,
    },
    "EUM CM": {
        "id": 5, "country": "CM", "name": "EUM",
        "slug": "eum", "currency": "XAF", "type": "mobile_money", "active": False,
    },

    # =========================================================================
    # SERVICES GÉNÉRIQUES
    # =========================================================================
    "SPC": {
        "id": 6, "country": "*", "name": "SPC",
        "slug": "spc", "currency": "XAF", "type": "bank", "active": True,
    },
    "EU CASH": {
        "id": 13, "country": "*", "name": "EU Cash",
        "slug": "eu_cash", "currency": "EUR", "type": "cash", "active": False,
    },
    "BANK OPERATION": {
        "id": 14, "country": "*", "name": "Bank Operation",
        "slug": "bank", "currency": "XAF", "type": "bank", "active": True,
    },
    "CARD": {
        "id": 23, "country": "*", "name": "Carte Bancaire",
        "slug": "card", "currency": "XAF", "type": "card", "active": False,
    },

    # =========================================================================
    # DEVISES (services de conversion / change)
    # =========================================================================
    "XAF": {
        "id": 15, "country": "*", "name": "XAF (FCFA)",
        "slug": "xaf", "currency": "XAF", "type": "currency", "active": True,
    },
    "USD": {
        "id": 16, "country": "*", "name": "USD (Dollar)",
        "slug": "usd", "currency": "USD", "type": "currency", "active": True,
    },
    "EUR": {
        "id": 17, "country": "*", "name": "EUR (Euro)",
        "slug": "eur", "currency": "EUR", "type": "currency", "active": True,
    },
    "SPC2": {
        "id": 18, "country": "*", "name": "SPC (bis)",
        "slug": "spc2", "currency": "XAF", "type": "bank", "active": True,
    },

    # =========================================================================
    # SÉNÉGAL
    # =========================================================================
    "OM SN": {
        "id": 24, "country": "SN", "name": "Orange Money",
        "slug": "orange", "currency": "XOF", "type": "mobile_money", "active": False,
    },
    "WAVE SN": {
        "id": 25, "country": "SN", "name": "Wave",
        "slug": "wave", "currency": "XOF", "type": "mobile_money", "active": False,
    },
    "FREE MONEY SN": {
        "id": 26, "country": "SN", "name": "Free Money",
        "slug": "free", "currency": "XOF", "type": "mobile_money", "active": False,
    },
    "EXPRESSO SN": {
        "id": 27, "country": "SN", "name": "Expresso",
        "slug": "expresso", "currency": "XOF", "type": "mobile_money", "active": False,
    },
    "WIZALL SN": {
        "id": 28, "country": "SN", "name": "Wizall",
        "slug": "wizall", "currency": "XOF", "type": "mobile_money", "active": False,
    },

    # =========================================================================
    # CÔTE D'IVOIRE
    # =========================================================================
    "OM CI": {
        "id": 29, "country": "CI", "name": "Orange Money",
        "slug": "orange", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "MOMO CI": {
        "id": 30, "country": "CI", "name": "MTN MoMo",
        "slug": "mtn", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "MOOV CI": {
        "id": 31, "country": "CI", "name": "Moov Money",
        "slug": "moov", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "WAVE CI": {
        "id": 32, "country": "CI", "name": "Wave",
        "slug": "wave", "currency": "XOF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # BURKINA FASO
    # =========================================================================
    "MOOV BF": {
        "id": 33, "country": "BF", "name": "Moov Money",
        "slug": "moov", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "OM BF": {
        "id": 34, "country": "BF", "name": "Orange Money",
        "slug": "orange", "currency": "XOF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # BÉNIN
    # =========================================================================
    "MOMO BJ": {
        "id": 35, "country": "BJ", "name": "MTN MoMo",
        "slug": "mtn", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "MOOV BJ": {
        "id": 36, "country": "BJ", "name": "Moov Money",
        "slug": "moov", "currency": "XOF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # TOGO
    # =========================================================================
    "T-MONEY TG": {
        "id": 37, "country": "TG", "name": "TMoney",
        "slug": "tmoney", "currency": "XOF", "type": "mobile_money", "active": True,
    },
    "MOOV TG": {
        "id": 38, "country": "TG", "name": "Moov Money",
        "slug": "moov", "currency": "XOF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # DEVISES UEMOA / AUTRES
    # =========================================================================
    "XOF": {
        "id": 41, "country": "*", "name": "XOF (FCFA)",
        "slug": "xof", "currency": "XOF", "type": "currency", "active": True,
    },
    "CDF": {
        "id": 42, "country": "*", "name": "CDF (Franc Congolais)",
        "slug": "cdf", "currency": "CDF", "type": "currency", "active": True,
    },
    "UGX": {
        "id": 43, "country": "*", "name": "UGX (Shilling Ougandais)",
        "slug": "ugx", "currency": "UGX", "type": "currency", "active": True,
    },

    # =========================================================================
    # RD CONGO
    # =========================================================================
    "VODACOM COD": {
        "id": 52, "country": "CD", "name": "Vodacom M-Pesa",
        "slug": "vodacom", "currency": "CDF", "type": "mobile_money", "active": True,
    },
    "AIRTEL COD": {
        "id": 53, "country": "CD", "name": "Airtel Money",
        "slug": "airtel", "currency": "CDF", "type": "mobile_money", "active": True,
    },
    "OM COD": {
        "id": 54, "country": "CD", "name": "Orange Money",
        "slug": "orange", "currency": "CDF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # CONGO BRAZZAVILLE
    # =========================================================================
    "AIRTEL COG": {
        "id": 55, "country": "CG", "name": "Airtel Money",
        "slug": "airtel", "currency": "XAF", "type": "mobile_money", "active": True,
    },
    "MOMO COG": {
        "id": 56, "country": "CG", "name": "MTN MoMo",
        "slug": "mtn", "currency": "XAF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # GABON
    # =========================================================================
    "AIRTEL GAB": {
        "id": 57, "country": "GA", "name": "Airtel Money",
        "slug": "airtel", "currency": "XAF", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # OUGANDA
    # =========================================================================
    "AIRTEL UGA": {
        "id": 58, "country": "UG", "name": "Airtel Money",
        "slug": "airtel", "currency": "UGX", "type": "mobile_money", "active": True,
    },
    "MOMO UGA": {
        "id": 59, "country": "UG", "name": "MTN MoMo",
        "slug": "mtn", "currency": "UGX", "type": "mobile_money", "active": True,
    },

    # =========================================================================
    # ZAMBIE
    # =========================================================================
    "AIRTEL ZMB": {
        "id": 60, "country": "ZM", "name": "Airtel Money",
        "slug": "airtel", "currency": "ZMW", "type": "mobile_money", "active": False,
    },
    "MOMO ZMB": {
        "id": 61, "country": "ZM", "name": "MTN MoMo",
        "slug": "mtn", "currency": "ZMW", "type": "mobile_money", "active": False,
    },
    "ZAMTEL ZMB": {
        "id": 62, "country": "ZM", "name": "Zamtel Money",
        "slug": "zamtel", "currency": "ZMW", "type": "mobile_money", "active": False,
    },
}


# =============================================================================
# Helpers
# =============================================================================

def get_operator_by_slug(country_code: str, slug: str) -> dict | None:
    """
    Retourne l'opérateur complet à partir du code pays et du slug.
    """
    for key, op in OPERATORS.items():
        if op["country"] == country_code.upper() and op["slug"] == slug.lower():
            return op
    return None


def get_operator_by_id(service_id: int) -> dict | None:
    """
    Retourne l'opérateur complet à partir de l'ID SoleasPay.
    """
    for key, op in OPERATORS.items():
        if op["id"] == service_id:
            return op
    return None


def get_active_operators_for_country(country_code: str) -> list[dict]:
    """
    Retourne la liste des opérateurs actifs pour un pays donné.
    """
    results = []
    for key, op in OPERATORS.items():
        if op["country"] == country_code.upper() and op["active"]:
            results.append(op)
    return results


def get_service_id(country_code: str, slug: str) -> int | None:
    """
    Retourne l'ID de service SoleasPay pour un pays et un slug d'opérateur.
    Exemple : get_service_id("TG", "tmoney") -> 37
    """
    op = get_operator_by_slug(country_code, slug)
    return op["id"] if op else None