"""
Moteur de transactions TransAfrik — Gestion métier des Transferts.

Ce module contient UNIQUEMENT la logique de base de données.
Aucune dépendance à SoleasPay, Flask, ou aux templates.

Fonctions disponibles :
  - create_transfer()           : Créer un nouveau transfert
  - mark_waiting_payment()      : En attente de paiement
  - mark_payment_processing()   : Pay-In en cours
  - mark_payment_success()      : Pay-In réussi
  - mark_payment_failed()       : Pay-In échoué
  - mark_withdraw_processing()  : Withdraw en cours
  - mark_completed()            : Transfert terminé
  - mark_failed()               : Transfert échoué
  - mark_cancelled()            : Transfert annulé
  - get_transfer()              : Récupérer un transfert par ID
  - get_transfer_by_reference() : Récupérer un transfert par référence
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from models import db, Transfer


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------

def create_transfer(
    sender_user_id: int,
    sender_name: str,
    sender_phone: str,
    sender_country: str,
    sender_operator: str,
    sender_operator_id: int,
    receiver_name: str,
    receiver_phone: str,
    receiver_country: str,
    receiver_operator: str,
    receiver_operator_id: int,
    amount: int,
    fees: int,
    total_amount: int,
    currency: str = 'XOF',
    exchange_rate: float = 1.0,
    sender_email: Optional[str] = None,
) -> Transfer:
    """
    Crée un nouveau transfert avec le statut initial CREATED.

    Args:
        sender_user_id      : ID de l'utilisateur expéditeur
        sender_name         : Nom complet de l'expéditeur
        sender_phone        : Téléphone de l'expéditeur
        sender_country      : Code pays expéditeur (ex: CI)
        sender_operator     : Nom de l'opérateur expéditeur
        sender_operator_id  : ID SoleasPay de l'opérateur expéditeur
        receiver_name       : Nom complet du destinataire
        receiver_phone      : Téléphone du destinataire
        receiver_country    : Code pays destinataire
        receiver_operator   : Nom de l'opérateur destinataire
        receiver_operator_id: ID SoleasPay de l'opérateur destinataire
        amount              : Montant en unités mineures
        fees                : Frais en unités mineures
        total_amount        : Montant total (amount + fees)
        currency            : Code devise (XOF, XAF, CDF, etc.)
        exchange_rate       : Taux de change (1.0 par défaut)
        sender_email        : Email de l'expéditeur (optionnel)

    Returns:
        Transfer: L'objet transfert créé.
    """
    transfer = Transfer(
        sender_user_id=sender_user_id,
        sender_name=sender_name,
        sender_email=sender_email,
        sender_phone=sender_phone,
        sender_country=sender_country.upper(),
        sender_operator=sender_operator,
        sender_operator_id=sender_operator_id,
        receiver_name=receiver_name,
        receiver_phone=receiver_phone,
        receiver_country=receiver_country.upper(),
        receiver_operator=receiver_operator,
        receiver_operator_id=receiver_operator_id,
        amount=amount,
        fees=fees,
        total_amount=total_amount,
        currency=currency.upper(),
        exchange_rate=exchange_rate,
        status='CREATED',
    )

    db.session.add(transfer)
    db.session.commit()
    return transfer


# ---------------------------------------------------------------------------
# Transitions de statut
# ---------------------------------------------------------------------------

def _transition(transfer: Transfer, new_status: str) -> Transfer:
    """Applique une transition de statut et persiste."""
    transfer.status = new_status
    transfer.updated_at = datetime.utcnow()
    db.session.commit()
    return transfer


def mark_waiting_payment(transfer: Transfer) -> Transfer:
    """Marque le transfert comme en attente de paiement."""
    return _transition(transfer, 'WAITING_PAYMENT')


def mark_payment_processing(
    transfer: Transfer,
    payin_reference: Optional[str] = None,
    payin_external_reference: Optional[str] = None,
) -> Transfer:
    """Marque le transfert comme Pay-In en cours de traitement.

    Args:
        transfer                : Le transfert à mettre à jour
        payin_reference         : Référence SoleasPay du Pay-In
        payin_external_reference: Référence externe (order_id côté client)
    """
    transfer.status = 'PAYMENT_PROCESSING'
    transfer.updated_at = datetime.utcnow()
    if payin_reference:
        transfer.payin_reference = payin_reference
    if payin_external_reference:
        transfer.payin_external_reference = payin_external_reference
    db.session.commit()
    return transfer


def mark_payment_success(
    transfer: Transfer,
    payin_response: Optional[Dict[str, Any]] = None,
) -> Transfer:
    """Marque le Pay-In comme réussi et stocke la réponse SoleasPay.

    Args:
        transfer       : Le transfert à mettre à jour
        payin_response : Réponse JSON brute de SoleasPay (optionnel)
    """
    transfer.status = 'PAYMENT_SUCCESS'
    transfer.updated_at = datetime.utcnow()
    if payin_response:
        transfer.payin_response = payin_response
        # Extraire la référence si présente dans la réponse
        data = payin_response.get('data', {})
        if isinstance(data, dict):
            if not transfer.payin_reference and data.get('reference'):
                transfer.payin_reference = data['reference']
            if not transfer.payin_external_reference and data.get('external_reference'):
                transfer.payin_external_reference = data['external_reference']
    db.session.commit()
    return transfer


def mark_payment_failed(
    transfer: Transfer,
    payin_response: Optional[Dict[str, Any]] = None,
) -> Transfer:
    """Marque le Pay-In comme échoué.

    Args:
        transfer       : Le transfert à mettre à jour
        payin_response : Réponse JSON brute de SoleasPay (optionnel)
    """
    transfer.status = 'PAYMENT_FAILED'
    transfer.updated_at = datetime.utcnow()
    if payin_response:
        transfer.payin_response = payin_response
    db.session.commit()
    return transfer


def mark_withdraw_processing(
    transfer: Transfer,
    withdraw_reference: Optional[str] = None,
    withdraw_external_reference: Optional[str] = None,
) -> Transfer:
    """Marque le transfert comme Withdraw en cours.

    Args:
        transfer                   : Le transfert à mettre à jour
        withdraw_reference          : Référence SoleasPay du Withdraw
        withdraw_external_reference : Référence externe du Withdraw
    """
    transfer.status = 'WITHDRAW_PROCESSING'
    transfer.updated_at = datetime.utcnow()
    if withdraw_reference:
        transfer.withdraw_reference = withdraw_reference
    if withdraw_external_reference:
        transfer.withdraw_external_reference = withdraw_external_reference
    db.session.commit()
    return transfer


def mark_completed(
    transfer: Transfer,
    withdraw_response: Optional[Dict[str, Any]] = None,
) -> Transfer:
    """Marque le transfert comme COMPLETED (terminé avec succès).

    Args:
        transfer          : Le transfert à mettre à jour
        withdraw_response : Réponse JSON brute de SoleasPay (optionnel)
    """
    transfer.status = 'COMPLETED'
    transfer.updated_at = datetime.utcnow()
    if withdraw_response:
        transfer.withdraw_response = withdraw_response
        # Extraire la référence si présente
        data = withdraw_response.get('data', {})
        if isinstance(data, dict):
            if not transfer.withdraw_reference and data.get('reference'):
                transfer.withdraw_reference = data['reference']
        elif isinstance(data, list) and len(data) > 0:
            if not transfer.withdraw_reference and data[0].get('reference'):
                transfer.withdraw_reference = data[0]['reference']
    db.session.commit()
    return transfer


def mark_failed(
    transfer: Transfer,
    reason: Optional[str] = None,
    webhook_payload: Optional[Dict[str, Any]] = None,
) -> Transfer:
    """Marque le transfert comme FAILED (échec définitif).

    Args:
        transfer        : Le transfert à mettre à jour
        reason          : Message d'erreur (optionnel)
        webhook_payload : Payload webhook (optionnel)
    """
    transfer.status = 'FAILED'
    transfer.updated_at = datetime.utcnow()
    if webhook_payload:
        transfer.webhook_payload = webhook_payload
    db.session.commit()
    return transfer


def mark_cancelled(transfer: Transfer) -> Transfer:
    """Marque le transfert comme CANCELLED (annulé par l'utilisateur)."""
    return _transition(transfer, 'CANCELLED')


# ---------------------------------------------------------------------------
# Récupération
# ---------------------------------------------------------------------------

def get_transfer(transfer_id: int) -> Optional[Transfer]:
    """Récupère un transfert par son ID primaire."""
    return Transfer.query.get(transfer_id)


def get_transfer_by_reference(reference: str) -> Optional[Transfer]:
    """Récupère un transfert par sa référence unique."""
    return Transfer.query.filter_by(reference=reference).first()


def get_transfers_for_user(
    user_id: int,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Transfer]:
    """Récupère les transferts d'un utilisateur, avec filtres optionnels.

    Args:
        user_id : ID de l'utilisateur
        status  : Filtrer par statut (optionnel)
        limit   : Nombre max de résultats
        offset  : Offset pour pagination

    Returns:
        Liste de Transfer.
    """
    q = Transfer.query.filter_by(sender_user_id=user_id)
    if status:
        q = q.filter_by(status=status.upper())
    return q.order_by(Transfer.created_at.desc()).offset(offset).limit(limit).all()


def count_transfers_for_user(user_id: int, status: Optional[str] = None) -> int:
    """Compte le nombre de transferts d'un utilisateur.

    Args:
        user_id : ID de l'utilisateur
        status  : Filtrer par statut (optionnel)

    Returns:
        Nombre de transferts.
    """
    q = Transfer.query.filter_by(sender_user_id=user_id)
    if status:
        q = q.filter_by(status=status.upper())
    return q.count()