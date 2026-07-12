"""
Client SoleasPay — Couche service bas niveau (aucune dépendance Flask).

Toutes les requêtes HTTP vers l'API SoleasPay transitent par ce fichier.

Endpoints :
  - pay_in()    -> POST /api/agent/bills/v3    (Pay-In : collecter un paiement)
  - withdraw()  -> POST /api/action/account/withdraw  (Payout : envoyer de l'argent)

Configuration via variables d'environnement :
  SOLEAS_API_KEY       : clé API (utilisée dans le header x-api-key pour pay_in)
  SOLEAS_BEARER_TOKEN  : token Bearer pour les opérations de retrait
  SOLEAS_WALLET        : numéro du wallet SoleasPay
  SOLEAS_BASE_URL      : URL de base (défaut : https://soleaspay.com)
"""

import os
import json
import logging
from typing import Optional, Dict, Any

import requests

logger = logging.getLogger("soleaspay")
logger.setLevel(logging.DEBUG)

# Ajout d'un handler console si aucun n'est présent (pratique pour le debug)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)

# ---------------------------------------------------------------------------
# Configuration depuis l'environnement
# ---------------------------------------------------------------------------
SOLEAS_API_KEY = os.getenv("SOLEAS_API_KEY", "")
SOLEAS_BEARER_TOKEN = os.getenv("SOLEAS_BEARER_TOKEN", "")
SOLEAS_WALLET = os.getenv("SOLEAS_WALLET", "")
SOLEAS_BASE_URL = os.getenv("SOLEAS_BASE_URL", "https://soleaspay.com")

# ---------------------------------------------------------------------------
# Pay-In : Collecter un paiement depuis un client Mobile Money
# ---------------------------------------------------------------------------

def pay_in(
    service: int,
    wallet: str,
    amount: float,
    currency: str,
    order_id: str,
    description: str = "",
    payer: str = "",
    payer_email: str = "",
    success_url: str = "",
    failure_url: str = "",
    otp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Collecte un paiement (Pay-In) via l'API SoleasPay.

    POST /api/agent/bills/v3
    Headers :
        x-api-key       : SOLEAS_API_KEY
        operation       : 2
        service         : ID du service (ex: 29 pour OM CI)
        Content-Type    : application/json
    Body :
        wallet          : Numéro du wallet à débiter
        amount          : Montant du paiement
        currency        : Code devise (XAF, XOF, CDF, etc.)
        order_id        : Identifiant unique de commande (côté TransAfrik)
        description     : Description du paiement
        payer           : Nom du payeur
        payer_email     : Email du payeur (reçu de confirmation)
        success_url     : URL de callback succès
        failure_url     : URL de callback échec
        otp             : (optionnel) Code OTP pour Orange Money

    Returns:
        dict: Réponse JSON de SoleasPay.
    """
    url = f"{SOLEAS_BASE_URL}/api/agent/bills/v3"

    headers = {
        "x-api-key": SOLEAS_API_KEY,
        "operation": "2",
        "service": str(service),
        "Content-Type": "application/json",
    }

    body = {
        "wallet": wallet,
        "amount": amount,
        "currency": currency,
        "order_id": order_id,
        "description": description,
        "payer": payer,
        "payerEmail": payer_email,
        "successUrl": success_url,
        "failureUrl": failure_url,
    }
    if otp:
        body["otp"] = otp

    # ---- LOGGING ----
    logger.info("=" * 50)
    logger.info("====== PAY IN ======")
    logger.info(f"URL     : {url}")
    logger.info(f"Headers : {json.dumps(headers, indent=2)}")
    logger.info(f"Body    : {json.dumps(body, indent=2)}")
    logger.info("=" * 50)

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=60)

        # ---- LOGGING RÉPONSE ----
        logger.info(f"Status  : {resp.status_code}")
        try:
            logger.info(f"Response: {json.dumps(resp.json(), indent=2)}")
        except Exception:
            logger.info(f"Response: {resp.text[:500]}")
        logger.info("=" * 50)

        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        logger.error(f"pay_in() failed: {e}")
        return {"success": False, "message": str(e), "code": 0, "status": "ERROR"}


# ---------------------------------------------------------------------------
# Withdraw / Payout : Envoyer de l'argent vers un bénéficiaire
# ---------------------------------------------------------------------------

def withdraw(
    service: int,
    wallet: str,
    amount: float,
    currency: str = "",
) -> Dict[str, Any]:
    """
    Retire de l'argent du compte SoleasPay vers un compte bénéficiaire (Payout).

    POST /api/action/account/withdraw
    Headers :
        Authorization   : Bearer {SOLEAS_BEARER_TOKEN}
        operation       : 4
        service         : ID du service (ex: 37 pour T-MONEY TG)
        Content-Type    : application/json
    Body :
        wallet          : Numéro du wallet bénéficiaire
        amount          : Montant à envoyer
        currency        : (optionnel) Code devise

    Returns:
        dict: Réponse JSON de SoleasPay.
    """
    url = f"{SOLEAS_BASE_URL}/api/action/account/withdraw"

    headers = {
        "Authorization": f"Bearer {SOLEAS_BEARER_TOKEN}",
        "operation": "4",
        "service": str(service),
        "Content-Type": "application/json",
    }

    body = {
        "wallet": wallet,
        "amount": amount,
    }
    if currency:
        body["currency"] = currency

    # ---- LOGGING ----
    logger.info("=" * 50)
    logger.info("====== WITHDRAW ======")
    logger.info(f"URL     : {url}")
    logger.info(f"Headers : {json.dumps(_mask_sensitive(headers), indent=2)}")
    logger.info(f"Body    : {json.dumps(body, indent=2)}")
    logger.info("=" * 50)

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=60)

        # ---- LOGGING RÉPONSE ----
        logger.info(f"Status  : {resp.status_code}")
        try:
            logger.info(f"Response: {json.dumps(resp.json(), indent=2)}")
        except Exception:
            logger.info(f"Response: {resp.text[:500]}")
        logger.info("=" * 50)

        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        logger.error(f"withdraw() failed: {e}")
        return {"success": False, "message": str(e), "code": 0, "status": "ERROR"}


# ---------------------------------------------------------------------------
# Helper : Masque le token Bearer dans les logs
# ---------------------------------------------------------------------------

def convert_currency(amount: float, from_currency: str, to_currency: str) -> Dict[str, Any]:
    """Conversion de devise via l'API SoleasPay.

    Endpoint : GET /api/convert?amount=100&from=XOF&to=USD

    Args:
        amount: Montant à convertir.
        from_currency: Code devise source (ex: XOF).
        to_currency: Code devise cible (ex: USD).

    Returns:
        dict: Réponse JSON de SoleasPay.
    """
    url = f"{SOLEAS_BASE_URL}/api/convert"
    params = {
        "amount": amount,
        "from": from_currency.upper(),
        "to": to_currency.upper(),
    }

    logger.info("=" * 50)
    logger.info("====== CONVERT ======")
    logger.info(f"URL     : {url}")
    logger.info(f"Params  : {json.dumps(params)}")
    logger.info("=" * 50)

    try:
        resp = requests.get(url, params=params, timeout=30)

        logger.info(f"Status  : {resp.status_code}")
        try:
            logger.info(f"Response: {json.dumps(resp.json(), indent=2)}")
        except Exception:
            logger.info(f"Response: {resp.text[:500]}")
        logger.info("=" * 50)

        resp.raise_for_status()
        return resp.json()

    except requests.RequestException as e:
        logger.error(f"convert_currency() failed: {e}")
        return {"success": False, "message": str(e), "code": 0}


def _mask_sensitive(headers: Dict[str, str]) -> Dict[str, str]:
    """Remplace le token Bearer par une version tronquée pour les logs."""
    masked = dict(headers)
    auth = masked.get("Authorization", "")
    if auth.startswith("Bearer ") and len(auth) > 30:
        masked["Authorization"] = auth[:20] + "..." + auth[-10:]
    return masked