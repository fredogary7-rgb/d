"""
Service de réception d'argent — Receive Money.
Permet aux utilisateurs de créer des demandes de paiement,
générer des QR codes de demande, et tracer les paiements reçus.
"""

import uuid
import random
import string
import json
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask

from models import db, User, PaymentRequest, TransactionReceive


# ═══════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════

REQUEST_CODE_LENGTH = 8
DEFAULT_EXPIRY_HOURS = 48
BASE_URL = "https://transafrik.org"


# ═══════════════════════════════════════════════════════════
# GÉNÉRATION DE CODE DE DEMANDE
# ═══════════════════════════════════════════════════════════

def generate_request_code(length: int = REQUEST_CODE_LENGTH) -> str:
    """Génère un code de demande unique alphanumérique."""
    chars = string.ascii_uppercase + string.digits
    # Éviter les caractères ambigus
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '').replace('L', '')
    code = ''.join(random.choices(chars, k=length))
    # Vérifier l'unicité
    while PaymentRequest.query.filter_by(request_code=code).first():
        code = ''.join(random.choices(chars, k=length))
    return code


def generate_receive_reference() -> str:
    """Génère une référence unique pour une transaction reçue."""
    now = datetime.utcnow()
    date_part = now.strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:8].upper()
    return f'RCV{date_part}{random_part}'


# ═══════════════════════════════════════════════════════════
# GÉNÉRATION DE QR CODE DE DEMANDE
# ═══════════════════════════════════════════════════════════

def generate_request_qrcode(request_code: str, amount: int, currency: str,
                             description: str = "") -> str:
    """Génère un QR code pour une demande de paiement.

    Args:
        request_code: Le code unique de la demande (ex: 9HF52KJ3)
        amount: Montant en unités mineures
        currency: Code devise (XOF, EUR, etc.)
        description: Description optionnelle

    Returns:
        Image PNG encodée en base64 (data URI)
    """
    payment_url = f"{BASE_URL}/request/{request_code}"

    payload = {
        "type": "transafrik_request",
        "version": "1.0",
        "request_code": request_code,
        "amount": amount,
        "currency": currency,
        "description": description,
        "url": payment_url,
    }
    qr_data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(qr_data_json)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=RadialGradiantColorMask(
            back_color=(255, 255, 255),
            center_color=(37, 99, 235),       # blue-600
            edge_color=(5, 150, 105),          # emerald-600
        ),
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ═══════════════════════════════════════════════════════════
# GÉNÉRATION DE QR CODE PAIEMENT (PAY LINK)
# ═══════════════════════════════════════════════════════════

def generate_pay_qrcode(pay_url: str) -> str:
    """Génère un QR code pointant vers une URL de paiement.

    Args:
        pay_url: L'URL de paiement (ex: https://transafrik.org/pay/@username)

    Returns:
        Image PNG encodée en base64 (data URI)
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(pay_url)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=RadialGradiantColorMask(
            back_color=(255, 255, 255),
            center_color=(37, 99, 235),
            edge_color=(5, 150, 105),
        ),
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# ═══════════════════════════════════════════════════════════
# CRÉATION DE DEMANDE DE PAIEMENT
# ═══════════════════════════════════════════════════════════

def create_payment_request(
    user: User,
    amount: int,
    currency: str = "XOF",
    description: str = "",
    expiry_hours: int = DEFAULT_EXPIRY_HOURS,
) -> Tuple[bool, Optional[PaymentRequest], Optional[str]]:
    """Crée une nouvelle demande de paiement.

    Args:
        user: L'utilisateur qui demande le paiement (receveur)
        amount: Montant en unités mineures
        currency: Code devise
        description: Description de la demande
        expiry_hours: Durée de validité en heures

    Returns:
        Tuple (success, payment_request_or_None, error_message_or_None)
    """
    if amount <= 0:
        return False, None, "Le montant doit être supérieur à 0."

    request_code = generate_request_code()
    expires_at = datetime.utcnow() + timedelta(hours=expiry_hours)
    payment_link = f"{BASE_URL}/request/{request_code}"
    qr_data = generate_request_qrcode(request_code, amount, currency, description)

    payment_request = PaymentRequest(
        request_code=request_code,
        receiver_id=user.id,
        amount=amount,
        currency=currency,
        description=description or f"Demande de paiement de {user.fullname}",
        status="PENDING",
        expires_at=expires_at,
        payment_link=payment_link,
        qr_data=qr_data,
    )
    db.session.add(payment_request)
    db.session.commit()

    return True, payment_request, None


def cancel_payment_request(user_id: int, request_code: str) -> Tuple[bool, Optional[str]]:
    """Annule une demande de paiement.

    Args:
        user_id: ID de l'utilisateur propriétaire de la demande
        request_code: Code de la demande

    Returns:
        Tuple (success, error_message_or_None)
    """
    pr = PaymentRequest.query.filter_by(
        request_code=request_code, receiver_id=user_id
    ).first()
    if not pr:
        return False, "Demande introuvable."
    if pr.status != "PENDING":
        return False, f"Impossible d'annuler une demande au statut '{pr.status}'."

    pr.status = "CANCELLED"
    pr.updated_at = datetime.utcnow()
    db.session.commit()
    return True, None


def get_payment_request_by_code(request_code: str) -> Optional[PaymentRequest]:
    """Récupère une demande de paiement par son code."""
    return PaymentRequest.query.filter_by(request_code=request_code).first()


def get_payment_request_by_uuid(uuid_str: str) -> Optional[PaymentRequest]:
    """Récupère une demande de paiement par son UUID."""
    return PaymentRequest.query.filter_by(uuid=uuid_str).first()


# ═══════════════════════════════════════════════════════════
# HISTORIQUE
# ═══════════════════════════════════════════════════════════

def get_user_payment_requests(user_id: int, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Récupère l'historique des demandes de paiement d'un utilisateur."""
    query = PaymentRequest.query.filter_by(receiver_id=user_id).order_by(
        PaymentRequest.created_at.desc()
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "requests": [pr.to_dict() for pr in pagination.items],
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    }


def get_recent_received_payments(user_id: int, limit: int = 10) -> list:
    """Récupère les paiements récents reçus par un utilisateur."""
    transactions = TransactionReceive.query.filter_by(
        receiver_id=user_id, status="completed"
    ).order_by(TransactionReceive.created_at.desc()).limit(limit).all()

    result = []
    for tx in transactions:
        sender = User.query.get(tx.sender_id) if tx.sender_id else None
        result.append({
            "id": tx.id,
            "amount": tx.amount,
            "currency": tx.currency,
            "status": tx.status,
            "reference": tx.reference,
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
            "sender_name": sender.fullname if sender else "Inconnu",
            "sender_email": sender.email if sender else None,
            "sender_photo": sender.profile_picture if sender else None,
            "payment_request_id": tx.payment_request_id,
        })
    return result


# ═══════════════════════════════════════════════════════════
# TRAITEMENT DE PAIEMENT (PAY)
# ═══════════════════════════════════════════════════════════

def process_receive_payment(
    request_code: str,
    sender_id: int,
    amount: int,
    currency: str,
) -> Tuple[bool, Optional[TransactionReceive], Optional[str]]:
    """Traite un paiement reçu via une demande de paiement.

    Args:
        request_code: Code de la demande de paiement
        sender_id: ID de l'utilisateur qui paie
        amount: Montant payé en unités mineures
        currency: Devise

    Returns:
        Tuple (success, transaction_or_None, error_message_or_None)
    """
    pr = PaymentRequest.query.filter_by(request_code=request_code).first()
    if not pr:
        return False, None, "Demande de paiement introuvable."

    if pr.status == "EXPIRED":
        return False, None, "Cette demande de paiement a expiré."
    if pr.status == "CANCELLED":
        return False, None, "Cette demande de paiement a été annulée."
    if pr.status == "PAID":
        return False, None, "Cette demande de paiement a déjà été payée."

    if pr.expires_at and pr.expires_at < datetime.utcnow():
        pr.status = "EXPIRED"
        pr.updated_at = datetime.utcnow()
        db.session.commit()
        return False, None, "Cette demande de paiement a expiré."

    if amount < pr.amount:
        return False, None, f"Le montant minimum est de {pr.amount} {pr.currency}."

    # Créer la transaction
    reference = generate_receive_reference()
    tx = TransactionReceive(
        payment_request_id=pr.id,
        sender_id=sender_id,
        receiver_id=pr.receiver_id,
        amount=amount,
        currency=currency,
        status="completed",
        reference=reference,
    )
    db.session.add(tx)

    # Mettre à jour la demande
    pr.status = "PAID"
    pr.sender_id = sender_id
    pr.payment_reference = reference
    pr.paid_at = datetime.utcnow()
    pr.updated_at = datetime.utcnow()

    # Créditer le receveur
    receiver = User.query.get(pr.receiver_id)
    if receiver:
        receiver.balance = (receiver.balance or 0) + amount

    # Débiter le payeur
    sender = User.query.get(sender_id)
    if sender and sender.balance >= amount:
        sender.balance = sender.balance - amount

    db.session.commit()

    return True, tx, None


# ═══════════════════════════════════════════════════════════
# TRAITEMENT DE PAIEMENT LIBRE (PAY LINK)
# ═══════════════════════════════════════════════════════════

def process_free_payment(
    sender_id: int,
    receiver_id: int,
    amount: int,
    currency: str = "XOF",
) -> Tuple[bool, Optional[Any], Optional[str]]:
    """Traite un paiement libre (sans demande préalable) vers un utilisateur.

    Le sender est débité de (amount + 2% fees). Le receiver reçoit amount.
    Les fees sont conservés par la plateforme.

    Args:
        sender_id: ID de l'utilisateur qui paie
        receiver_id: ID de l'utilisateur qui reçoit
        amount: Montant envoyé au receiver en unités mineures
        currency: Devise

    Returns:
        Tuple (success, {transaction, fee}, error_message_or_None)
    """
    import math

    if sender_id == receiver_id:
        return False, None, "Vous ne pouvez pas vous payer vous-même."

    if amount <= 0:
        return False, None, "Le montant doit être supérieur à 0."

    # Frais plateforme : 2% plafonnés à 5000 XOF
    fee = min(math.ceil(amount * 0.02), 5000)
    total_debit = amount + fee

    # Vérifier les utilisateurs
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)

    if not sender or not receiver:
        return False, None, "Utilisateur introuvable."

    if (sender.balance or 0) < total_debit:
        return False, None, (
            f"Solde insuffisant. Votre solde est de {sender.balance} {currency}. "
            f"Vous devez {total_debit} {currency} (montant {amount} + frais {fee})."
        )

    # Créer la transaction receive
    reference = generate_receive_reference()
    tx = TransactionReceive(
        payment_request_id=None,
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        currency=currency,
        status="completed",
        reference=reference,
        description=(
            f"Paiement libre de {sender.fullname or sender.username}"
            f" à {receiver.fullname or receiver.username}"
        ),
    )
    db.session.add(tx)

    # Créditer le receveur (montant net)
    receiver.balance = (receiver.balance or 0) + amount

    # Débiter le payeur (montant + frais)
    sender.balance = (sender.balance or 0) - total_debit
    sender.used_daily = (sender.used_daily or 0) + total_debit

    db.session.commit()

    return True, {"transaction": tx, "fee": fee}, None


# ═══════════════════════════════════════════════════════════
# RECHERCHE D'UTILISATEUR
# ═══════════════════════════════════════════════════════════

def search_user_for_payment(query: str) -> Optional[Dict[str, Any]]:
    """Recherche un utilisateur pour un paiement par username, email, téléphone ou UUID.

    Args:
        query: Terme de recherche (ex: username, email partiel, phone, UUID)

    Returns:
        Dictionnaire utilisateur si trouvé, None sinon
    """
    # 1) Chercher par username (partie avant @) — prioritaire
    user = User.query.filter(
        User.email.ilike(f"{query}@%")
    ).first()

    # 2) Chercher par QR identifier (UUID) — exact match
    if not user:
        user = User.query.filter(User.qr_identifier == query).first()

    # 3) Chercher par phone partiel
    if not user:
        user = User.query.filter(User.phone.ilike(f"%{query}%")).first()

    # 4) Chercher par email partiel (fallback large)
    if not user:
        user = User.query.filter(User.email.ilike(f"%{query}%")).first()

    if not user:
        return None

    return {
        "id": user.id,
        "fullname": user.fullname or "Utilisateur",
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "country": user.country,
        "currency": user.currency,
        "profile_picture": user.profile_picture,
        "qr_identifier": user.qr_identifier,
        "kyc_status": user.kyc_status,
    }


# ═══════════════════════════════════════════════════════════
# NETTOYAGE DES DEMANDES EXPIRÉES
# ═══════════════════════════════════════════════════════════

def expire_old_requests():
    """Marque comme expirées toutes les demandes dont la date d'expiration est passée."""
    now = datetime.utcnow()
    expired = PaymentRequest.query.filter(
        PaymentRequest.status == "PENDING",
        PaymentRequest.expires_at < now,
    ).all()
    for pr in expired:
        pr.status = "EXPIRED"
        pr.updated_at = now
    if expired:
        db.session.commit()
    return len(expired)