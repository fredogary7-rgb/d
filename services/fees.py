"""
Moteur de calcul des frais de transfert — TransAfrik.

Architecture extensible :
    - Grille de frais par défaut (tranches de montant)
    - Surcharges par pays (sender_country / receiver_country)
    - Surcharges par opérateur (sender_operator / receiver_operator)
    - Promotions temporaires (code promo)
    - Frais VIP (utilisateurs premium)
    - Frais personnalisés (par utilisateur)

Utilisation :
    from services.fees import calculate_fee

    result = calculate_fee(
        amount=10000,
        sender_country="TG",
        receiver_country="BJ",
        sender_operator="tmoney",
        receiver_operator="mtn",
        promo_code=None,
        user_tier="standard",
        user_id=None,
    )
    print(result)  # -> {'fees': 300, 'receiver_gets': 9700, 'total': 10000, ...}
"""

from __future__ import annotations
import math
from datetime import datetime, timedelta
from typing import Optional


# ═══════════════════════════════════════════════════════════
# GRILLE DE FRAIS PAR DÉFAUT (tranches de montant)
# Modifier UNIQUEMENT cette section pour changer les tarifs.
# Format : (min_amount_inclusive, max_amount_inclusive, frais_fixe)
# La dernière tranche peut avoir max=None (= infini)
# ═══════════════════════════════════════════════════════════

FEE_TIERS: list[tuple[int, Optional[int], int | str]] = [
    (0, None, "4%"),  # 4% sur tous les montants
]

# Délai de transfert estimé par défaut (secondes)
DEFAULT_ESTIMATED_TIME_SECONDS = 30


# ═══════════════════════════════════════════════════════════
# SURCHARGES PAR PAYS (optionnel)
# Si un pays n'est pas listé, la grille par défaut s'applique.
# Format : { "CODE_PAYS": [tranches] }
# ═══════════════════════════════════════════════════════════

COUNTRY_FEE_OVERRIDES: dict[str, list[tuple[int, Optional[int], int | str]]] = {
    # Exemple : "CM": [(0, 10_000, 500), (10_001, None, "1.2%")],
    # Décommenter et adapter pour activer des tarifs spécifiques par pays.
}

# ═══════════════════════════════════════════════════════════
# SURCHARGES PAR OPÉRATEUR (optionnel)
# Format : { "slug_operateur": { "fee_modifier": "1.1x" } }
#           OU { "slug_operateur": { "fixed_override": [(0, None, 500)] } }
# ═══════════════════════════════════════════════════════════

OPERATOR_FEE_OVERRIDES: dict[str, dict] = {
    # Exemple : "orange": {"fee_modifier": "1.1x"},  # 10% plus cher
    # Exemple : "wave": {"fixed_override": [(0, None, 250)]},  # frais fixe 250
    # Décommenter pour activer.
}

# ═══════════════════════════════════════════════════════════
# PROMOTIONS
# Format : { "CODE_PROMO": {"discount": "20%", "expires": "2026-12-31"} }
# ═══════════════════════════════════════════════════════════

PROMO_CODES: dict[str, dict] = {
    # Exemple : "BIENVENUE": {"discount": "50%", "expires": "2026-12-31", "max_discount": 500},
    # Exemple : "VIP2026": {"discount": "100%", "expires": "2026-12-31", "max_discount": 1000},
}

# ═══════════════════════════════════════════════════════════
# FRAIS VIP (par tier utilisateur)
# Format : { "tier": {"discount": "20%", "max_discount": 500} }
# ═══════════════════════════════════════════════════════════

VIP_DISCOUNTS: dict[str, dict] = {
    "standard": {"discount": "0%"},
    "silver":   {"discount": "10%", "max_discount": 500},
    "gold":     {"discount": "25%", "max_discount": 1000},
    "platinum": {"discount": "50%", "max_discount": 2000},
}

# ═══════════════════════════════════════════════════════════
# FRAIS PERSONNALISÉS PAR UTILISATEUR (user_id -> tiers)
# Sera chargé depuis la base de données plus tard.
# Format : { user_id: [(min, max, fee), ...] }
# ═══════════════════════════════════════════════════════════

USER_CUSTOM_FEES: dict[int, list[tuple[int, Optional[int], int | str]]] = {
    # Exemple : 42: [(0, None, 0)],  # utilisateur 42 : frais gratuits
}


# ═══════════════════════════════════════════════════════════
# MOTEUR DE CALCUL
# ═══════════════════════════════════════════════════════════


def _resolve_tiers(
    amount: int,
    sender_country: str = "",
    receiver_country: str = "",
    sender_operator: str = "",
    receiver_operator: str = "",
    user_id: Optional[int] = None,
) -> list[tuple[int, Optional[int], int | str]]:
    """
    Résout la grille de frais applicable selon les paramètres.

    Ordre de priorité :
        1. Frais personnalisés (user_id)
        2. Frais opérateur (fixed_override)
        3. Frais pays (receiver_country, puis sender_country)
        4. Grille par défaut

    Returns:
        list[tuple]: Grille applicable [(min, max, fee), ...]
    """
    # 1. Frais personnalisés par utilisateur
    if user_id and user_id in USER_CUSTOM_FEES:
        return USER_CUSTOM_FEES[user_id]

    # 2. Override fixe par opérateur destinataire
    op_slug = receiver_operator.lower() if receiver_operator else ""
    if op_slug in OPERATOR_FEE_OVERRIDES:
        override = OPERATOR_FEE_OVERRIDES[op_slug]
        if "fixed_override" in override:
            return override["fixed_override"]

    # 3. Override par pays destinataire
    if receiver_country in COUNTRY_FEE_OVERRIDES:
        return COUNTRY_FEE_OVERRIDES[receiver_country]

    # 4. Override par pays émetteur
    if sender_country in COUNTRY_FEE_OVERRIDES:
        return COUNTRY_FEE_OVERRIDES[sender_country]

    # 5. Grille par défaut
    return FEE_TIERS


def _compute_fee_from_tiers(
    amount: int,
    tiers: list[tuple[int, Optional[int], int | str]],
) -> int:
    """
    Calcule les frais à partir d'une grille de tranches.

    Chaque tranche = (min, max, fee) où fee peut être :
        - un int : frais fixe
        - une str "X%" : pourcentage du montant
        - une str "X.Yx" : multiplicateur (non utilisé ici, réservé)

    Returns:
        int: Frais calculés, arrondis à l'entier supérieur.
    """
    if amount <= 0:
        return 0

    fee = 0
    for min_val, max_val, fee_rule in tiers:
        if amount < min_val:
            continue
        if max_val is not None and amount > max_val:
            continue

        if isinstance(fee_rule, str):
            fee_rule_str = fee_rule.strip().lower()
            if fee_rule_str.endswith("%"):
                pct = float(fee_rule_str[:-1])
                fee = amount * pct / 100.0
            else:
                # Fallback : essayer de parser comme int
                fee = int(fee_rule_str)
        else:
            fee = fee_rule
        break

    return int(math.ceil(fee))


def _apply_operator_modifier(
    fee: int,
    sender_operator: str = "",
    receiver_operator: str = "",
) -> int:
    """
    Applique un modificateur multiplicatif par opérateur (ex: "1.1x").
    """
    for op_slug in ((receiver_operator or "").lower(), (sender_operator or "").lower()):
        if not op_slug:
            continue
        op_override = OPERATOR_FEE_OVERRIDES.get(op_slug, {})
        modifier = op_override.get("fee_modifier", "")
        if isinstance(modifier, str) and modifier.endswith("x"):
            mult = float(modifier[:-1])
            fee = int(math.ceil(fee * mult))
            break
    return fee


def _apply_promo(fee: int, promo_code: Optional[str] = None) -> tuple[int, str]:
    """
    Applique une réduction promo.

    Returns:
        tuple[int, str]: (frais_après_promo, message_promo)
    """
    if not promo_code:
        return fee, ""

    promo = PROMO_CODES.get(promo_code.upper())
    if not promo:
        return fee, f"Code promo « {promo_code} » invalide"

    # Vérifier expiration
    expires_str = promo.get("expires", "")
    if expires_str:
        try:
            expires = datetime.strptime(expires_str, "%Y-%m-%d")
            if datetime.utcnow() > expires:
                return fee, f"Code promo « {promo_code} » expiré"
        except ValueError:
            pass

    discount_str = promo.get("discount", "0%")
    max_discount = promo.get("max_discount", None)

    if discount_str.endswith("%"):
        pct = float(discount_str[:-1])
        reduction = fee * pct / 100.0
        if max_discount is not None:
            reduction = min(reduction, max_discount)
        new_fee = max(0, int(math.ceil(fee - reduction)))
        return new_fee, f"Promo « {promo_code} » appliquée (-{discount_str})"

    return fee, ""


def _apply_vip_discount(fee: int, user_tier: str = "standard") -> int:
    """
    Applique la réduction VIP selon le tier de l'utilisateur.
    """
    tier_config = VIP_DISCOUNTS.get(user_tier.lower(), VIP_DISCOUNTS["standard"])
    discount_str = tier_config.get("discount", "0%")
    max_discount = tier_config.get("max_discount", None)

    if discount_str.endswith("%"):
        pct = float(discount_str[:-1])
        if pct <= 0:
            return fee
        reduction = fee * pct / 100.0
        if max_discount is not None:
            reduction = min(reduction, max_discount)
        fee = max(0, int(math.ceil(fee - reduction)))
    return fee


def calculate_fee(
    amount: int,
    sender_country: str = "",
    receiver_country: str = "",
    sender_operator: str = "",
    receiver_operator: str = "",
    promo_code: Optional[str] = None,
    user_tier: str = "standard",
    user_id: Optional[int] = None,
) -> dict:
    """
    Calcule les frais de transfert.

    Args:
        amount:            Montant envoyé (unités mineures, ex: 10000 = 10 000 XOF).
        sender_country:    Code pays émetteur (ex: "TG").
        receiver_country:  Code pays destinataire (ex: "BJ").
        sender_operator:   Slug opérateur émetteur (ex: "tmoney").
        receiver_operator: Slug opérateur destinataire (ex: "mtn").
        promo_code:        Code promotionnel optionnel.
        user_tier:         Tier utilisateur ("standard", "silver", "gold", "platinum").
        user_id:           ID utilisateur pour frais personnalisés.

    Returns:
        dict avec les clés :
            - amount:          Montant envoyé
            - fees:            Frais de transfert
            - receiver_gets:   Montant reçu par le destinataire (= amount, inchangé)
            - total:           Total à payer (= amount + fees)
            - estimated_time:  Temps estimé (secondes)
            - promo_message:   Message promo (si applicable)
            - tier_discount:   Réduction VIP appliquée (0 si standard)
    """
    if amount <= 0:
        return {
            "amount": 0,
            "fees": 0,
            "receiver_gets": 0,
            "total": 0,
            "estimated_time": 0,
            "promo_message": "",
            "tier_discount": 0,
        }

    # 1. Résoudre la grille applicable
    tiers = _resolve_tiers(
        amount=amount,
        sender_country=sender_country,
        receiver_country=receiver_country,
        sender_operator=sender_operator,
        receiver_operator=receiver_operator,
        user_id=user_id,
    )

    # 2. Calculer les frais bruts
    raw_fee = _compute_fee_from_tiers(amount, tiers)

    # 3. Appliquer modificateur opérateur (ex: 1.1x)
    raw_fee = _apply_operator_modifier(raw_fee, sender_operator, receiver_operator)

    # 4. Appliquer réduction VIP
    fee_before_promo = _apply_vip_discount(raw_fee, user_tier)
    tier_discount = raw_fee - fee_before_promo

    # 5. Appliquer code promo
    final_fee, promo_message = _apply_promo(fee_before_promo, promo_code)

    return {
        "amount": amount,
        "fees": final_fee,
        "receiver_gets": amount,
        "total": amount + final_fee,
        "estimated_time": DEFAULT_ESTIMATED_TIME_SECONDS,
        "promo_message": promo_message,
        "tier_discount": tier_discount,
    }