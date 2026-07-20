"""
Service de retrait — TransAfrik.
Gère les retraits directs vers Mobile Money / Compte bancaire via SoleasPay.

Fonctions :
- submit_withdraw(user, data) → dict { success, withdrawal, ... }
- check_withdraw_status(withdrawal_id) → dict
- refund_withdrawal(withdrawal_id) → dict
- get_operators_by_country(country_code) → list
- get_available_countries() → list
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from models import db, User, Withdrawal, Transaction
from services.soleaspay import withdraw as soleaspay_withdraw, convert_currency
from services.fees import calculate_fee
from services.email_service import _send_email as send_email
from services.push_service import send_push_to_user
from config.operators import OPERATORS

logger = logging.getLogger(__name__)

# --------------------------
# Constantes
# --------------------------
MIN_WITHDRAWAL_AMOUNT = 500  # unités mineures (5 XOF/USD/...)


def get_available_countries() -> List[Dict[str, Any]]:
    """Retourne la liste des pays disponibles pour les retraits (opérateurs actifs)."""
    seen = set()
    countries = []
    for key, op in OPERATORS.items():
        if op.get("active") and op.get("type") in ("mobile_money", "bank") and op["country"] != "*":
            code = op["country"]
            if code not in seen:
                seen.add(code)
                countries.append({
                    "code": code,
                    "name": _country_name(code),
                    "flag": _country_flag(code),
                    "currency": op["currency"],
                })
    countries.sort(key=lambda c: c["name"])
    return countries


def get_operators_by_country(country_code: str) -> List[Dict[str, Any]]:
    """Retourne les opérateurs actifs de retrait pour un pays donné."""
    ops = []
    for key, op in OPERATORS.items():
        if op.get("active") and op["country"] == country_code and op.get("type") in ("mobile_money", "bank"):
            ops.append({
                "id": op["id"],
                "name": op["name"],
                "slug": op["slug"],
                "currency": op["currency"],
                "type": op["type"],
            })
    ops.sort(key=lambda o: o["name"])
    return ops


def _get_operator_info(operator_id: int) -> Optional[Dict[str, Any]]:
    """Retrouve les infos d'un opérateur par son ID SoleasPay."""
    for key, op in OPERATORS.items():
        if op["id"] == operator_id:
            return dict(op)
    return None


def _country_name(code: str) -> str:
    names = {
        "TG": "Togo", "BJ": "Bénin", "CI": "Côte d'Ivoire",
        "CM": "Cameroun", "SN": "Sénégal", "BF": "Burkina Faso",
        "ML": "Mali", "NE": "Niger", "GA": "Gabon",
        "CD": "RD Congo", "CG": "Congo", "GH": "Ghana",
        "NG": "Nigeria", "RW": "Rwanda", "KE": "Kenya",
        "UG": "Ouganda", "TZ": "Tanzanie", "ZM": "Zambie",
    }
    return names.get(code, code)


def _country_flag(code: str) -> str:
    """Génère un emoji drapeau à partir du code pays ISO."""
    if len(code) != 2:
        return "🌍"
    regional = "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())
    return regional


def submit_withdraw(user: User, data: Dict[str, Any]) -> Dict[str, Any]:
    """Soumet un retrait vers Mobile Money.

    Args:
        user: Utilisateur connecté.
        data: {
            "operator_id": int,
            "phone": str,
            "amount": float,     # en devise display (ex: 5000.00 XOF)
            "currency": str,      # XOF, XAF, USD, EUR
            "recipient_name": str (optional)
        }

    Returns:
        dict: { success: bool, error: str (optionnel), withdrawal: Withdrawal (optionnel) }
    """
    operator_id = data.get("operator_id")
    phone = data.get("phone", "").strip()
    amount_display = data.get("amount")
    currency = data.get("currency", "XOF").upper()
    recipient_name = data.get("recipient_name", "").strip() or None

    # ---- Validation 1 : Opérateur ----
    op_info = _get_operator_info(int(operator_id)) if operator_id else None
    if not op_info:
        return {"success": False, "error": "Opérateur invalide ou non supporté."}

    # ---- Validation 2 : Montant minimum ----
    try:
        amount_display = float(amount_display)
    except (TypeError, ValueError):
        return {"success": False, "error": "Montant invalide."}

    amount_minor = int(round(amount_display * 100))
    if amount_minor < MIN_WITHDRAWAL_AMOUNT:
        return {"success": False,
                "error": f"Montant minimum : {MIN_WITHDRAWAL_AMOUNT / 100:.2f} {currency}."}

    # ---- Validation 3 : Numéro ----
    phone = phone.replace(" ", "").replace("-", "").replace(".", "")
    if not phone.isdigit() or len(phone) < 6:
        return {"success": False,
                "error": "Numéro de téléphone invalide (min 6 chiffres)."}

    # ---- Validation 4 : Devise compatible ----
    op_currency = op_info.get("currency", "XOF")
    if currency != op_currency:
        try:
            conv = convert_currency(amount_display, currency, op_currency)
            if conv.get("success", True) is False:
                return {"success": False, "error": f"Conversion {currency} → {op_currency} impossible."}
            converted_display = float(conv.get("result", amount_display))
            converted_minor = int(round(converted_display * 100))
        except Exception:
            return {"success": False, "error": f"Erreur de conversion {currency} → {op_currency}."}
    else:
        converted_minor = amount_minor

    # ---- Validation 5 : Calcul des frais ----
    fee_result = _calculate_withdrawal_fee(
        amount=converted_minor,
        sender_country=user.country,
        receiver_country=op_info["country"],
        receiver_operator=op_info["slug"],
    )
    fees = fee_result["fees"]
    total_debited = converted_minor + fees

    # ---- Validation 6 : Solde suffisant ----
    if user.balance < total_debited:
        return {"success": False, "error": "Solde insuffisant."}

    # ---- Créer l'enregistrement ----
    withdrawal = Withdrawal(
        user_id=user.id,
        recipient_name=recipient_name,
        recipient_phone=phone,
        recipient_country=op_info["country"],
        recipient_operator=op_info["name"],
        recipient_operator_id=operator_id,
        amount=converted_minor,
        currency=op_currency,
        fees=fees,
        total_debited=total_debited,
        exchange_rate=amount_minor / converted_minor if (converted_minor and amount_minor != converted_minor) else 1.0,
        status="CREATED",
    )
    db.session.add(withdrawal)
    db.session.flush()  # Pour obtenir withdrawal.id avant le commit

    # ---- Débiter le portefeuille ----
    user.balance -= total_debited
    withdrawal.status = "WAITING_WITHDRAW"
    withdrawal.updated_at = datetime.now(timezone.utc)

    # ---- Créer une transaction comptable ----
    txn = Transaction(
        user_id=user.id,
        type="withdraw",
        amount=converted_minor,
        currency=op_currency,
        fee=fees,
        status="processing",
        recipient_name=recipient_name or op_info["name"],
        recipient_phone=phone,
        recipient_country=op_info["country"],
        recipient_operator=op_info["name"],
    )
    db.session.add(txn)

    # ---- Appeler SoleasPay ----
    request_payload = {
        "service": int(operator_id),
        "wallet": phone,
        "amount": float(converted_minor),
        "currency": op_currency,
    }
    withdrawal.request_payload = json.dumps(request_payload)

    try:
        resp = soleaspay_withdraw(
            service=int(operator_id),
            wallet=phone,
            amount=float(converted_minor),
            currency=op_currency,
        )
        withdrawal.response_payload = json.dumps(resp)
        withdrawal.withdraw_reference = resp.get("reference", "")
        withdrawal.external_reference = resp.get("external_reference", "")

        if resp.get("success", True) is False or resp.get("status") in ("FAILED", "REJECTED", "CANCELLED", "ERROR"):
            _handle_failed_withdrawal(withdrawal, user, txn, resp)
            db.session.commit()
            return {"success": False, "error": resp.get("message", "Le retrait a échoué.")}

        withdrawal.status = "WITHDRAW_PROCESSING"
        db.session.commit()

        return {"success": True, "withdrawal": withdrawal, "message": "Retrait en cours de traitement."}

    except Exception as e:
        logger.error(f"Exception lors du retrait: {e}")
        _handle_failed_withdrawal(withdrawal, user, txn, {"status": "ERROR", "message": str(e)})
        db.session.commit()
        return {"success": False, "error": "Erreur technique. Veuillez réessayer."}


def _calculate_withdrawal_fee(amount: int, sender_country: str,
                              receiver_country: str, receiver_operator: str) -> dict:
    """Calcule les frais pour un retrait."""
    try:
        result = calculate_fee(
            amount=amount,
            sender_country=sender_country,
            receiver_country=receiver_country,
            sender_operator=None,
            receiver_operator=receiver_operator,
            promo_code=None,
            user_tier="standard",
            user_id=None,
        )
        return {
            "fees": result.get("fees", 0),
            "receiver_gets": amount,
            "total": amount + result.get("fees", 0),
        }
    except Exception as e:
        logger.error(f"[WITHDRAW_FEE] Erreur calcul frais: {e}", exc_info=True)
        return {"fees": 0, "receiver_gets": amount, "total": amount}


def _handle_failed_withdrawal(withdrawal: Withdrawal, user: User, txn: Transaction, resp: dict):
    """Gère l'échec d'un retrait : rembourse et notifie."""
    user.balance += withdrawal.total_debited
    withdrawal.status = "FAILED"
    withdrawal.status_message = resp.get("message", "Échec du retrait")
    withdrawal.refunded = True
    withdrawal.refund_amount = withdrawal.total_debited
    withdrawal.refund_at = datetime.now(timezone.utc)
    txn.status = "failed"
    withdrawal.updated_at = datetime.now(timezone.utc)

    # Notification
    try:
        _notify_withdrawal(user, withdrawal, success=False)
    except Exception:
        pass


def process_withdrawal_webhook(withdrawal: Withdrawal, webhook_data: dict) -> bool:
    """Traite le webhook SoleasPay pour un retrait.

    Appelé depuis le webhook existant /webhook/soleaspay quand le type est 'withdraw'/'payout'.

    Returns:
        bool: True si le retrait a été complété avec succès.
    """
    status = webhook_data.get("status", "").upper()

    if status in ("SUCCESS", "COMPLETED", "APPROVED"):
        withdrawal.status = "COMPLETED"
        withdrawal.status_message = "Retrait effectué avec succès."
        withdrawal.updated_at = datetime.now(timezone.utc)

        # Mettre à jour la transaction associée
        txn = Transaction.query.filter_by(
            user_id=withdrawal.user_id,
            recipient_phone=withdrawal.recipient_phone,
            type="withdraw",
            status="processing",
        ).order_by(Transaction.created_at.desc()).first()
        if txn:
            txn.status = "success"
            txn.updated_at = datetime.now(timezone.utc)

        # Notification de succès
        try:
            _notify_withdrawal(withdrawal.user, withdrawal, success=True)
        except Exception:
            pass

        db.session.commit()
        return True

    elif status in ("FAILED", "REJECTED", "CANCELLED"):
        if withdrawal.status != "FAILED":
            withdrawal.status = "FAILED"
            withdrawal.status_message = webhook_data.get("message", "Retrait refusé.")
            withdrawal.updated_at = datetime.now(timezone.utc)

            # Remboursement
            user = withdrawal.user
            user.balance += withdrawal.total_debited
            withdrawal.refunded = True
            withdrawal.refund_amount = withdrawal.total_debited
            withdrawal.refund_at = datetime.now(timezone.utc)

            # Transaction
            txn = Transaction.query.filter_by(
                user_id=withdrawal.user_id,
                recipient_phone=withdrawal.recipient_phone,
                type="withdraw",
                status="processing",
            ).order_by(Transaction.created_at.desc()).first()
            if txn:
                txn.status = "failed"

            _notify_withdrawal(user, withdrawal, success=False)
            db.session.commit()

        return False

    return False


def _notify_withdrawal(user: User, withdrawal: Withdrawal, success: bool = True):
    """Envoie les notifications (email + push) après un retrait."""
    amount_str = f"{withdrawal.amount_display():.2f} {withdrawal.currency}"
    operator = withdrawal.recipient_operator

    if success:
        subject = "Retrait effectué"
        body_html = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:500px;margin:0 auto;">
            <h2 style="color:#2563EB;">Retrait effectué ✅</h2>
            <p>Votre retrait de <strong>{amount_str}</strong> vers <strong>{operator}</strong> a été effectué avec succès.</p>
            <p>Référence : <code>{withdrawal.reference}</code></p>
            <p style="color:#6B7280;font-size:12px;">Pays : {_country_name(withdrawal.recipient_country)}</p>
        </div>
        """
    else:
        subject = "Échec du retrait"
        body_html = f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:500px;margin:0 auto;">
            <h2 style="color:#EF4444;">Échec du retrait ❌</h2>
            <p>Votre retrait de <strong>{amount_str}</strong> vers <strong>{operator}</strong> a échoué.</p>
            <p>Le montant a été remboursé sur votre portefeuille.</p>
            <p>Référence : <code>{withdrawal.reference}</code></p>
        </div>
        """

    # Email
    if user.email:
        try:
            send_email(to_email=user.email, subject=subject, html_body=body_html)
        except Exception as e:
            logger.error(f"Notification email échouée: {e}")

    # Push
    try:
        send_push_to_user(
            user_id=user.id,
            title=subject,
            body=body_html.replace('<div style="font-family:Inter,Arial,sans-serif;max-width:500px;margin:0 auto;">', '')
                          .replace('</div>', '')
                          .replace('<br>', '\n')
                          .replace('<strong>', '').replace('</strong>', '')
                          .replace('<code>', '').replace('</code>', '')
                          .replace('<p>', '').replace('</p>', '\n')
                          .replace('<h2 style="color:#2563EB;">', '').replace('<h2 style="color:#EF4444;">', '')
                          .replace('</h2>', ''),
            url=f"/withdraw",
        )
    except Exception as e:
        logger.error(f"Notification push échouée: {e}")


def get_withdrawal_history(user_id: int, page: int = 1, per_page: int = 10) -> dict:
    """Retourne l'historique des retraits d'un utilisateur."""
    query = Withdrawal.query.filter_by(user_id=user_id).order_by(Withdrawal.created_at.desc())
    total = query.count()
    withdrawals = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "withdrawals": [w.to_dict() for w in withdrawals],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def status_label(status: str) -> str:
    labels = {
        "CREATED": "Créé",
        "WAITING_WITHDRAW": "En attente",
        "WITHDRAW_PROCESSING": "En cours",
        "COMPLETED": "Succès",
        "FAILED": "Échec",
        "REJECTED": "Refusé",
        "CANCELLED": "Annulé",
    }
    return labels.get(status, status)