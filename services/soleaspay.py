"""
Client SoleasPay — Couche service bas niveau (aucune dépendance Flask).

Toutes les requêtes HTTP vers l'API SoleasPay transitent par ce fichier.

Endpoints :
  - pay_in()        -> POST /api/agent/bills/v3       (Pay-In : collecter un paiement)
  - obtenir_token() -> POST /api/action/auth           (obtention du Bearer token)
  - withdraw()      -> POST /api/action/account/withdraw  (Payout : envoyer de l'argent)

Configuration via variables d'environnement :
  SOLEAS_API_KEY        : clé API publique (PUBLIC_API_KEY pour l'auth)
  PRIVATE_SECRET_KEY    : clé secrète (utilisée avec PUBLIC_API_KEY pour /api/action/auth)
  SOLEAS_WALLET         : numéro du wallet SoleasPay
  SOLEAS_BASE_URL       : URL de base (défaut : https://soleaspay.com)
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
SOLEAS_API_KEY = os.getenv("SOLEAS_API_KEY", "")                # PUBLIC_API_KEY
PRIVATE_SECRET_KEY = os.getenv("PRIVATE_SECRET_KEY", "")         # clé secrète
SOLEAS_WALLET = os.getenv("SOLEAS_WALLET", "")
SOLEAS_BASE_URL = os.getenv("SOLEAS_BASE_URL", "https://soleaspay.com")

# Cache du token (évite de rappeler /api/action/auth à chaque withdraw)
_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0}

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
# Authentification : obtention du token Bearer
# ---------------------------------------------------------------------------

def obtenir_token() -> str:
    """Obtient un access_token via POST /api/action/auth.

    Utilise PUBLIC_API_KEY (x-api-key) et PRIVATE_SECRET_KEY (x-private-key).

    Returns:
        str: access_token valide (jamais vide).

    Raises:
        RuntimeError: si les variables d'environnement sont manquantes,
                      si l'API ne renvoie pas de access_token,
                      ou si la requête échoue.
    """
    # ---- Vérification des variables d'environnement ----
    if not SOLEAS_API_KEY:
        raise RuntimeError(
            "Impossible d'obtenir le token SoleasPay : "
            "SOLEAS_API_KEY (PUBLIC_API_KEY) est vide. "
            "Vérifiez la variable d'environnement SOLEAS_API_KEY."
        )
    if not PRIVATE_SECRET_KEY:
        raise RuntimeError(
            "Impossible d'obtenir le token SoleasPay : "
            "PRIVATE_SECRET_KEY est vide. "
            "Vérifiez la variable d'environnement PRIVATE_SECRET_KEY."
        )

    url = f"{SOLEAS_BASE_URL}/api/action/auth"
    headers = {
        "x-api-key": SOLEAS_API_KEY,
        "x-private-key": PRIVATE_SECRET_KEY,
        "Content-Type": "application/json",
    }

    logger.info("=" * 50)
    logger.info("====== OBTENIR TOKEN ======")
    logger.info(f"URL            : {url}")
    logger.info(f"x-api-key      : {SOLEAS_API_KEY[:15]}... (len={len(SOLEAS_API_KEY)})")
    logger.info(f"x-private-key  : {PRIVATE_SECRET_KEY[:15]}... (len={len(PRIVATE_SECRET_KEY)})")
    logger.info("=" * 50)

    try:
        resp = requests.post(url, headers=headers, timeout=30)
        logger.info(f"Status auth    : {resp.status_code}")
        logger.info(f"Response auth  : {resp.text[:1000]}")

        resp.raise_for_status()
        data = resp.json()
        logger.info(f"JSON parsé     : {json.dumps(data, indent=2)[:500]}")

        access_token = data.get("access_token") or data.get("token") or data.get("data", {}).get("access_token")

        if not access_token:
            logger.error(f"Aucun access_token trouvé dans la réponse. Clés disponibles : {list(data.keys())}")
            raise RuntimeError(
                "Impossible d'obtenir le token SoleasPay : "
                "access_token absent de la réponse de /api/action/auth."
            )

        logger.info(f"Token obtenu   : len={len(str(access_token))}, preview={str(access_token)[:10]}...")
        return access_token

    except requests.RequestException as e:
        logger.error(f"Échec auth SoleasPay : {e}")
        raise RuntimeError(f"Impossible d'obtenir le token SoleasPay : {e}") from e


# ---------------------------------------------------------------------------
# Withdraw / Payout : Envoyer de l'argent vers un bénéficiaire
# ---------------------------------------------------------------------------

def withdraw(
    service: int,
    wallet: str,
    amount: float,
    currency: str = "",
) -> Dict[str, Any]:
    """Retire de l'argent du compte SoleasPay vers un compte bénéficiaire (Payout).

    POST /api/action/account/withdraw
    Headers :
        Authorization   : Bearer {access_token} (obtenu via obtenir_token())
        operation       : 4
        service         : ID du service
        Content-Type    : application/json
    Body :
        wallet          : Numéro du wallet bénéficiaire
        amount          : Montant à envoyer
        currency        : (optionnel) Code devise

    Returns:
        dict: Réponse JSON de SoleasPay.
    """
    # ---- Obtention dynamique du token ----
    try:
        token = obtenir_token()
    except RuntimeError as e:
        logger.error(f"Impossible d'appeler withdraw() : {e}")
        return {"success": False, "message": str(e), "code": 0, "status": "ERROR"}

    if not token:
        logger.critical("obtenir_token() a retourné une chaîne vide — withdraw() annulé")
        return {"success": False, "message": "Token d'authentification vide.", "code": 0, "status": "ERROR"}

    logger.info(f"Token length for withdraw: {len(token)}")

    url = f"{SOLEAS_BASE_URL}/api/action/account/withdraw"

    headers = {
        "Authorization": f"Bearer {token}",
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