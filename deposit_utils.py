"""
Utilitaires pour la gestion des dépôts (alimentation du portefeuille TransAfrik).

Ce module contient :
  - Les pays autorisés pour les dépôts
  - La fonction de calcul des frais de dépôt
  - La génération de référence de dépôt
"""

import uuid
from datetime import datetime
from config.operators import get_active_operators_for_country

# Pays autorisés pour les dépôts (avec drapeaux et noms)
DEPOSIT_COUNTRIES = [
    {"code": "TG", "name": "Togo", "flag": "🇹🇬", "currency": "XOF"},
    {"code": "BJ", "name": "Bénin", "flag": "🇧🇯", "currency": "XOF"},
    {"code": "CI", "name": "Côte d'Ivoire", "flag": "🇨🇮", "currency": "XOF"},
    {"code": "BF", "name": "Burkina Faso", "flag": "🇧🇫", "currency": "XOF"},
    {"code": "CM", "name": "Cameroun", "flag": "🇨🇲", "currency": "XAF"},
    {"code": "CD", "name": "RD Congo", "flag": "🇨🇩", "currency": "CDF"},
    {"code": "CG", "name": "Congo", "flag": "🇨🇬", "currency": "XAF"},
    {"code": "GA", "name": "Gabon", "flag": "🇬🇦", "currency": "XAF"},
    {"code": "UG", "name": "Ouganda", "flag": "🇺🇬", "currency": "UGX"},
    {"code": "ZM", "name": "Zambie", "flag": "🇿🇲", "currency": "ZMW"},
    {"code": "SN", "name": "Sénégal", "flag": "🇸🇳", "currency": "XOF"},
]


def get_deposit_operators_for_country(country_code: str) -> list[dict]:
    """
    Retourne les opérateurs actifs disponibles pour un pays donné.
    Filtre uniquement les opérateurs de type mobile_money.
    """
    operators = get_active_operators_for_country(country_code.upper())
    return [op for op in operators if op.get("type") == "mobile_money"]


def calculate_deposit_fees(amount: float, currency: str = "XOF") -> dict:
    """
    Calcule les frais de dépôt.
    Règle : 1.5% du montant, minimum 100 unités, maximum 5000 unités.
    """
    fee_rate = 0.015
    min_fee = 100
    max_fee = 5000

    fee = amount * fee_rate
    fee = max(min_fee, min(fee, max_fee))
    fee = round(fee)

    total = amount + fee

    return {
        "amount": int(amount),
        "fees": fee,
        "total": total,
        "currency": currency,
    }


def generate_deposit_reference() -> str:
    """Génère une référence unique de dépôt (format: DEP-20260710-A83F91)."""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:6].upper()
    return f'DEP-{date_part}-{random_part}'