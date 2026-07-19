"""
Utilitaires pour les transferts d'argent.

Délègue le calcul des frais au moteur avancé services/fees.py
(tranches, pays, opérateurs, VIP, promos).
"""

from services.fees import calculate_fee as _engine_calculate_fee


def calculate_fees(
    amount: int,
    sender_country: str = "",
    receiver_country: str = "",
    sender_operator: str = "",
    receiver_operator: str = "",
    promo_code: str = None,
    user_tier: str = "standard",
    user_id: int = None,
) -> int:
    """
    Calcule les frais de transfert via le moteur avancé.

    Args:
        amount:            Montant envoyé (unités mineures).
        sender_country:    Code pays émetteur (ex: "TG").
        receiver_country:  Code pays destinataire (ex: "BJ").
        sender_operator:   Slug opérateur émetteur (ex: "tmoney").
        receiver_operator: Slug opérateur destinataire (ex: "mtn").
        promo_code:        Code promotionnel optionnel.
        user_tier:         Tier utilisateur ("standard", "silver", "gold", "platinum").
        user_id:           ID utilisateur pour frais personnalisés.

    Returns:
        int: Frais en unités mineures.
    """
    result = _engine_calculate_fee(
        amount=amount,
        sender_country=sender_country,
        receiver_country=receiver_country,
        sender_operator=sender_operator,
        receiver_operator=receiver_operator,
        promo_code=promo_code,
        user_tier=user_tier,
        user_id=user_id,
    )
    return result["fees"]


def calculate_total(
    amount: int,
    sender_country: str = "",
    receiver_country: str = "",
    sender_operator: str = "",
    receiver_operator: str = "",
    promo_code: str = None,
    user_tier: str = "standard",
    user_id: int = None,
) -> int:
    """
    Calcule le total à payer (montant + frais).

    Args:
        amount:            Montant envoyé (unités mineures).
        sender_country:    Code pays émetteur.
        receiver_country:  Code pays destinataire.
        sender_operator:   Slug opérateur émetteur.
        receiver_operator: Slug opérateur destinataire.
        promo_code:        Code promotionnel optionnel.
        user_tier:         Tier utilisateur.
        user_id:           ID utilisateur pour frais personnalisés.

    Returns:
        int: Total à payer.
    """
    return amount + calculate_fees(
        amount=amount,
        sender_country=sender_country,
        receiver_country=receiver_country,
        sender_operator=sender_operator,
        receiver_operator=receiver_operator,
        promo_code=promo_code,
        user_tier=user_tier,
        user_id=user_id,
    )


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