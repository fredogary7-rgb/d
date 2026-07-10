"""
Utilitaires pour les transferts d'argent.

Fonctions pures, sans dépendance Flask ni base de données.
"""

# Configuration des frais — sera déplacée en base de données ou fichier .env plus tard
FEE_PERCENTAGE = 1.0       # 1%
FEE_MINIMUM = 100          # minimum 100 FCFA (en unités mineures)
FEE_MAXIMUM = 10000        # plafond à 10 000 FCFA (optionnel, 0 = illimité)


def calculate_fees(amount: int) -> int:
    """
    Calcule les frais de transfert.

    Règle :
        - 1% du montant
        - Minimum 100 FCFA
        - Plafond 10 000 FCFA (si FEE_MAXIMUM > 0)

    Args:
        amount: Montant en unités mineures (ex: 5000 = 5000 XOF).

    Returns:
        int: Frais arrondis à l'entier supérieur, en unités mineures.
    """
    import math

    if amount <= 0:
        return 0

    fee = amount * FEE_PERCENTAGE / 100.0
    fee = max(FEE_MINIMUM, fee)
    if FEE_MAXIMUM > 0:
        fee = min(FEE_MAXIMUM, fee)
    fee = int(math.ceil(fee))

    return fee


def calculate_total(amount: int) -> int:
    """
    Calcule le total à payer (montant + frais).

    Args:
        amount: Montant en unités mineures.

    Returns:
        int: Total à payer.
    """
    return amount + calculate_fees(amount)


def format_currency(amount: int, currency: str = "XOF") -> str:
    """
    Formate un montant en devise lisible.

    Args:
        amount:   Montant en unités mineures.
        currency: Code devise.

    Returns:
        str: Montant formaté (ex: "5 000 XOF").
    """
    return f"{amount:,}".replace(",", " ") + f" {currency}"