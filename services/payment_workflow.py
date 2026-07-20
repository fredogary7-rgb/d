"""
Workflow d'orchestration SoleasPay — Orchestre le cycle de vie complet d'un transfert.

Ce module contient UNIQUEMENT la logique métier d'orchestration.
Aucune route Flask, aucun template, aucun JavaScript.

Cycle de vie :
    CREATED → WAITING_PAYMENT → PAYMENT_PROCESSING → PAYMENT_SUCCESS
                                                           ↓
                                                   WITHDRAW_PROCESSING
                                                           ↓
                                                       COMPLETED
    (ou FAILED / CANCELLED à toute étape)

Configuration via variables d'environnement :
    SOLEAS_SUCCESS_URL   : URL de callback succès (défaut : https://transafrik.com/payment/success)
    SOLEAS_FAILURE_URL   : URL de callback échec  (défaut : https://transafrik.com/payment/failure)
"""

import os
import logging
from typing import Dict, Any, Optional

from services.soleaspay import pay_in, withdraw, SOLEAS_WALLET
from services.push_service import send_push_to_user
from services.transfer_service import (
    mark_waiting_payment,
    mark_payment_processing,
    mark_payment_success,
    mark_payment_failed,
    mark_withdraw_processing,
    mark_completed,
    mark_failed,
)
from models import Transfer

logger = logging.getLogger("payment_workflow")
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)

# URLs de callback (configurables via .env)
SOLEAS_SUCCESS_URL = os.getenv(
    "SOLEAS_SUCCESS_URL", "https://transafrik.com/payment/success"
)
SOLEAS_FAILURE_URL = os.getenv(
    "SOLEAS_FAILURE_URL", "https://transafrik.com/payment/failure"
)


# =============================================================================
# Helpers — Interprétation des réponses SoleasPay
# =============================================================================

def is_processing(response: Dict[str, Any]) -> bool:
    """Vérifie si la réponse SoleasPay indique un traitement en cours."""
    if not isinstance(response, dict):
        return False
    return (
        response.get("success") is True
        and response.get("status") == "PROCESSING"
    )


def is_payment_success(response: Dict[str, Any]) -> bool:
    """Vérifie si la réponse/webhook SoleasPay indique un succès."""
    if not isinstance(response, dict):
        return False
    # Webhooks SoleasPay : {"success": true, "status": "SUCCESS"} (pas de "code")
    if response.get("success") is True and str(response.get("status", "")).upper() in ("SUCCESS", "COMPLETED", "APPROVED"):
        return True
    # Réponses API : {"success": true, "code": 200}
    return response.get("success") is True and response.get("code") in (200, 201)


def is_payment_failed(response: Dict[str, Any]) -> bool:
    """Vérifie si la réponse SoleasPay indique un échec."""
    if not isinstance(response, dict):
        return True  # Si pas de réponse, considérer comme échec
    return (
        response.get("success") is False
        or response.get("code") == 400
        or response.get("status") == "FAILURE"
        or response.get("status") == "FAILED"
    )


# =============================================================================
# Étape 1 : Démarrer le Pay-In
# =============================================================================

def start_transfer_payment(
    transfer: Transfer,
    success_url: Optional[str] = None,
    failure_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Démarre le Pay-In SoleasPay pour un transfert.

    Vérifications :
        - Le transfert doit être au statut CREATED

    Actions :
        1. Appelle SoleasPay.pay_in() avec les infos du transfert
        2. Si succès → PAYMENT_PROCESSING + enregistre les références
        3. Retourne le résultat

    Args:
        transfer    : L'objet Transfer à traiter
        success_url : URL de callback succès (override)
        failure_url : URL de callback échec (override)

    Returns:
        dict: {'success': bool, 'reference': str, 'message': str}
    """
    ref = transfer.reference

    logger.info("=" * 60)
    logger.info("[TRANSFER]")
    logger.info(f"Reference : {ref}")
    logger.info(f"Status    : {transfer.status} → WAITING_PAYMENT")

    # ---- Vérification du statut ----
    if transfer.status != "CREATED":
        logger.warning(f"Statut invalide pour Pay-In : {transfer.status}")
        return {
            "success": False,
            "reference": ref,
            "message": f"Le transfert n'est pas au statut CREATED (actuel: {transfer.status})",
        }

    # ---- Transition : en attente de paiement ----
    mark_waiting_payment(transfer)
    logger.info(f"Status    : WAITING_PAYMENT → lancement Pay-In")

    # ---- Payload pour SoleasPay ----
    s_success_url = success_url or SOLEAS_SUCCESS_URL
    s_failure_url = failure_url or SOLEAS_FAILURE_URL

    payin_result = pay_in(
        service=transfer.sender_operator_id,
        wallet=transfer.sender_phone,
        amount=transfer.total_amount,
        currency=transfer.currency,
        order_id=transfer.reference,
        description="TransAfrik Transfer",
        payer=transfer.sender_name,
        payer_email=transfer.sender_email or "",
        success_url=s_success_url,
        failure_url=s_failure_url,
    )

    # ---- Interprétation de la réponse ----
    if is_processing(payin_result):
        # Extraire les références de la réponse
        data = payin_result.get("data", {})
        payin_ref = data.get("reference", "") if isinstance(data, dict) else ""
        external_ref = data.get("external_reference", "") if isinstance(data, dict) else ""

        mark_payment_processing(
            transfer,
            payin_reference=payin_ref,
            payin_external_reference=external_ref,
        )
        # Stocker la réponse JSON complète
        transfer.payin_response = payin_result
        from models import db
        db.session.commit()

        logger.info(f"Status    : PAYMENT_PROCESSING ✅")
        logger.info(f"PayIn Ref : {payin_ref}")
        logger.info("=" * 60)

        return {
            "success": True,
            "reference": ref,
            "payin_reference": payin_ref,
            "message": "Paiement en cours de traitement",
        }

    elif is_payment_failed(payin_result):
        mark_payment_failed(transfer, payin_response=payin_result)

        logger.error(f"Status    : PAYMENT_FAILED ❌")
        logger.error(f"Erreur    : {payin_result.get('message', 'Inconnue')}")
        logger.info("=" * 60)

        return {
            "success": False,
            "reference": ref,
            "message": f"Échec du paiement : {payin_result.get('message', 'Erreur inconnue')}",
        }

    else:
        # Réponse inattendue — on loggue mais on ne bloque pas
        mark_payment_processing(transfer)
        transfer.payin_response = payin_result
        from models import db
        db.session.commit()

        logger.warning(f"Status    : PAYMENT_PROCESSING (réponse inattendue) ⚠️")
        logger.warning(f"Response  : {payin_result}")
        logger.info("=" * 60)

        return {
            "success": True,
            "reference": ref,
            "message": "Paiement envoyé (réponse inattendue, vérifier le statut)",
        }


# =============================================================================
# Étape 2 : Gérer le succès du Pay-In
# =============================================================================

def handle_payment_success(
    transfer: Transfer,
    payin_response: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Gère le succès du Pay-In et déclenche automatiquement le Withdraw.

    Actions :
        1. Marque le Pay-In comme réussi
        2. Lance automatiquement le retrait vers le bénéficiaire

    Args:
        transfer       : Le Transfer à traiter
        payin_response : Réponse SoleasPay reçue (webhook ou callback)

    Returns:
        dict avec le résultat des deux étapes
    """
    ref = transfer.reference

    logger.info("=" * 60)
    logger.info("[TRANSFER]")
    logger.info(f"Reference : {ref}")
    logger.info(f"Status    : {transfer.status} → PAYMENT_SUCCESS")

    # ---- Étape A : Marquer le Pay-In comme succès ----
    mark_payment_success(transfer, payin_response=payin_response)
    logger.info(f"Status    : PAYMENT_SUCCESS ✅")
    logger.info("↓")
    logger.info(f"Status    : lancement automatique du Withdraw")

    # ---- Étape B : Lancer automatiquement le Withdraw ----
    withdraw_result = start_withdraw(transfer)

    logger.info("=" * 60)

    return {
        "success": True,
        "reference": ref,
        "payment": "success",
        "withdraw": withdraw_result,
    }


# =============================================================================
# Étape 3 : Démarrer le Withdraw (Payout)
# =============================================================================

def start_withdraw(transfer: Transfer) -> Dict[str, Any]:
    """
    Déclenche le retrait (Payout) vers le bénéficiaire via SoleasPay.

    Actions :
        1. Appelle SoleasPay.withdraw()
        2. Si succès → WITHDRAW_PROCESSING + enregistre les références

    Args:
        transfer : Le Transfer à traiter

    Returns:
        dict: {'success': bool, 'reference': str, 'message': str}
    """
    ref = transfer.reference

    # ---- Payload pour SoleasPay ----
    withdraw_result = withdraw(
        service=transfer.receiver_operator_id,
        wallet=transfer.receiver_phone,
        amount=transfer.amount,  # Montant envoyé au bénéficiaire (hors frais)
        currency=transfer.currency,
    )

    # ---- Interprétation de la réponse ----
    if is_processing(withdraw_result):
        data = withdraw_result.get("data", {})
        # La réponse withdraw peut avoir data comme liste ou dict
        if isinstance(data, list) and len(data) > 0:
            w_ref = data[0].get("reference", "")
            w_ext = data[0].get("external_reference", "")
        elif isinstance(data, dict):
            w_ref = data.get("reference", "")
            w_ext = data.get("external_reference", "")
        else:
            w_ref = ""
            w_ext = ""

        mark_withdraw_processing(
            transfer,
            withdraw_reference=w_ref,
            withdraw_external_reference=w_ext,
        )
        transfer.withdraw_response = withdraw_result
        from models import db
        db.session.commit()

        logger.info(f"Status    : WITHDRAW_PROCESSING ✅")
        logger.info(f"Withdraw Ref : {w_ref}")
        logger.info("=" * 60)

        return {
            "success": True,
            "reference": ref,
            "withdraw_reference": w_ref,
            "message": "Retrait en cours de traitement",
        }

    elif is_payment_failed(withdraw_result):
        mark_failed(transfer, webhook_payload=withdraw_result)

        logger.error(f"Status    : FAILED ❌")
        logger.error(f"Erreur    : {withdraw_result.get('message', 'Inconnue')}")
        logger.info("=" * 60)

        return {
            "success": False,
            "reference": ref,
            "message": f"Échec du retrait : {withdraw_result.get('message', 'Erreur inconnue')}",
        }

    else:
        # Réponse inattendue
        mark_withdraw_processing(transfer)
        transfer.withdraw_response = withdraw_result
        from models import db
        db.session.commit()

        logger.warning(f"Status    : WITHDRAW_PROCESSING (réponse inattendue) ⚠️")
        logger.warning(f"Response  : {withdraw_result}")
        logger.info("=" * 60)

        return {
            "success": True,
            "reference": ref,
            "message": "Retrait envoyé (réponse inattendue, vérifier le statut)",
        }


# =============================================================================
# Étape 4 : Gérer le succès du Withdraw
# =============================================================================

def handle_withdraw_success(
    transfer: Transfer,
    withdraw_response: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Marque le transfert comme COMPLETED après un retrait réussi.

    Args:
        transfer          : Le Transfer à finaliser
        withdraw_response : Réponse SoleasPay reçue (webhook ou callback)

    Returns:
        dict: Confirmation
    """
    ref = transfer.reference

    logger.info("=" * 60)
    logger.info("[TRANSFER]")
    logger.info(f"Reference : {ref}")
    logger.info(f"Status    : {transfer.status} → COMPLETED")

    mark_completed(transfer, withdraw_response=withdraw_response)

    logger.info(f"Status    : COMPLETED 🎉")
    logger.info("=" * 60)

    # ---- Notification push à l'expéditeur ----
    try:
        from models import db, Notification
        send_push_to_user(
            user_id=transfer.sender_user_id,
            title="Transfert réussi ! 🎉",
            body=f"Votre transfert de {transfer.amount:,} {transfer.currency} vers {transfer.receiver_name} a été effectué avec succès.",
            url=f"/send-money/confirm?ref={transfer.reference}",
            tag=f"transfer-{transfer.reference}",
            data={"reference": transfer.reference, "amount": transfer.amount, "currency": transfer.currency},
        )
        # Notification in-app
        notif = Notification(
            user_id=transfer.sender_user_id,
            title="Transfert réussi",
            message=f"Votre transfert de {transfer.amount:,} {transfer.currency} vers {transfer.receiver_name} a été effectué avec succès.",
            type="transfer_success",
            data={"reference": transfer.reference},
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as push_err:
        logger.warning(f"[PUSH] Échec notification transfert réussi: {push_err}")

    return {
        "success": True,
        "reference": ref,
        "status": "COMPLETED",
        "message": "Transfert terminé avec succès",
    }


# =============================================================================
# Étape 5 : Gérer l'échec du Withdraw
# =============================================================================

def handle_withdraw_failed(
    transfer: Transfer,
    reason: Optional[str] = None,
    webhook_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Marque le transfert comme FAILED après un échec de retrait.

    Args:
        transfer        : Le Transfer à marquer comme échoué
        reason          : Message d'erreur
        webhook_payload : Payload webhook reçu

    Returns:
        dict: Confirmation
    """
    ref = transfer.reference

    logger.info("=" * 60)
    logger.info("[TRANSFER]")
    logger.info(f"Reference : {ref}")
    logger.info(f"Status    : {transfer.status} → FAILED")

    mark_failed(transfer, reason=reason, webhook_payload=webhook_payload)

    logger.error(f"Status    : FAILED ❌")
    if reason:
        logger.error(f"Raison    : {reason}")
    logger.info("=" * 60)

    # ---- Notification push à l'expéditeur ----
    try:
        from models import db, Notification
        send_push_to_user(
            user_id=transfer.sender_user_id,
            title="Transfert échoué ❌",
            body=f"Votre transfert de {transfer.amount:,} {transfer.currency} vers {transfer.receiver_name} a échoué : {reason or 'Erreur inconnue'}.",
            url=f"/send-money/confirm?ref={transfer.reference}",
            tag=f"transfer-{transfer.reference}",
            data={"reference": transfer.reference, "amount": transfer.amount, "currency": transfer.currency},
        )
        # Notification in-app
        notif = Notification(
            user_id=transfer.sender_user_id,
            title="Transfert échoué",
            message=f"Votre transfert de {transfer.amount:,} {transfer.currency} vers {transfer.receiver_name} a échoué : {reason or 'Erreur inconnue'}.",
            type="transfer_failed",
            data={"reference": transfer.reference},
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as push_err:
        logger.warning(f"[PUSH] Échec notification transfert échoué: {push_err}")

    return {
        "success": False,
        "reference": ref,
        "status": "FAILED",
        "message": reason or "Échec du transfert",
    }


# =============================================================================
# Workflow complet (tout-en-un)
# =============================================================================

def run_full_transfer_workflow(transfer: Transfer) -> Dict[str, Any]:
    """
    Exécute le workflow complet : Pay-In → Withdraw → Completed.

    Utilisé pour les tests ou les cas où tout est synchrone.
    En production, les étapes sont déclenchées par webhooks.

    Args:
        transfer : Le Transfer (doit être au statut CREATED)

    Returns:
        dict: Résultat complet du workflow
    """
    ref = transfer.reference
    workflow_log = []

    logger.info("=" * 60)
    logger.info("[WORKFLOW COMPLET]")
    logger.info(f"Reference : {ref}")
    logger.info("-" * 40)

    # Étape 1 : Pay-In
    payin = start_transfer_payment(transfer)
    workflow_log.append({"step": "pay_in", "result": payin})

    if not payin.get("success"):
        logger.error("Workflow arrêté : échec Pay-In")
        return {"success": False, "reference": ref, "workflow": workflow_log}

    # Étape 2 : Payment Success
    payment = handle_payment_success(transfer)
    workflow_log.append({"step": "payment_success", "result": payment})

    # Étape 3 : Withdraw était déjà lancé dans handle_payment_success
    # Vérifier le statut final
    if transfer.status == "COMPLETED":
        logger.info("Workflow terminé : COMPLETED 🎉")
        return {"success": True, "reference": ref, "status": "COMPLETED", "workflow": workflow_log}

    # Étape 4 : Withdraw Success
    withdraw_ok = handle_withdraw_success(transfer)
    workflow_log.append({"step": "withdraw_success", "result": withdraw_ok})

    logger.info("=" * 60)
    return {"success": True, "reference": ref, "status": "COMPLETED", "workflow": workflow_log}