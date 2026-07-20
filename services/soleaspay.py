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

def _essayer_auth(url: str, api_key: str, private_key: str, mode: str) -> Dict[str, Any]:
    """Essaie une authentification et retourne la réponse JSON parsée.

    Args:
        url: URL de l'endpoint /api/action/auth.
        api_key: clé publique (SOLEAS_API_KEY).
        private_key: clé privée (PRIVATE_SECRET_KEY).
        mode: "headers" → clés dans x-api-key / x-private-key
              "body"   → clés dans le JSON {public_key, private_key}

    Returns:
        dict: réponse JSON parsée (peut contenir code, message, access_token).
    """
    if mode == "headers":
        headers = {
            "x-api-key": api_key,
            "x-private-key": private_key,
            "Content-Type": "application/json",
        }
        body = None
        logger.info(f"[AUTH via HEADERS] x-api-key + x-private-key")
    else:
        headers = {"Content-Type": "application/json"}
        body = {"public_key": api_key, "private_key": private_key}
        logger.info(f"[AUTH via BODY JSON] public_key + private_key")

    logger.info(f"  URL            : {url}")
    for k, v in headers.items():
        if k.lower() in ("x-api-key", "x-private-key"):
            logger.info(f"  Header {k}: {v[:10]}...{v[-6:]} (len={len(v)})")
        else:
            logger.info(f"  Header {k}: {v}")
    if body:
        logger.info(f"  Body JSON      : public_key={api_key[:10]}... (len={len(api_key)}), "
                    f"private_key={private_key[:10]}... (len={len(private_key)})")

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    logger.info(f"  Status HTTP    : {resp.status_code}")
    logger.info(f"  Body réponse   : {resp.text[:500]}")

    try:
        data = resp.json()
    except Exception:
        data = {"_raw": resp.text[:500]}
    return data


def obtenir_token() -> str:
    """Obtient un access_token via POST /api/action/auth.

    Utilise SOLEAS_API_KEY (public_key) et PRIVATE_SECRET_KEY (private_key).
    Essaie d'abord les clés dans les headers, puis dans le body JSON si échec.

    Returns:
        str: access_token valide (jamais vide).

    Raises:
        RuntimeError: si les variables d'environnement sont manquantes,
                      si l'API ne renvoie pas de access_token,
                      ou si la requête échoue.
    """
    # ---- Chargement et nettoyage des variables d'environnement ----
    raw_api_key = os.getenv("SOLEAS_API_KEY", "")
    raw_private_key = os.getenv("PRIVATE_SECRET_KEY", "")

    api_key = raw_api_key.strip() if raw_api_key else ""
    private_key = raw_private_key.strip() if raw_private_key else ""

    # ---- Logs de diagnostic ----
    logger.info("=" * 70)
    logger.info("====== DIAGNOSTIC AUTH SOLEASPAY ======")
    logger.info(f"SOLEAS_API_KEY     : vide={not bool(raw_api_key)}, "
                f"len_raw={len(raw_api_key)}, len_stripped={len(api_key)}")
    if api_key:
        logger.info(f"  premiers car.   : {repr(api_key[:8])}")
        logger.info(f"  derniers car.   : {repr(api_key[-8:])}")
    logger.info(f"PRIVATE_SECRET_KEY : vide={not bool(raw_private_key)}, "
                f"len_raw={len(raw_private_key)}, len_stripped={len(private_key)}")
    if private_key:
        logger.info(f"  premiers car.   : {repr(private_key[:8])}")
        logger.info(f"  derniers car.   : {repr(private_key[-8:])}")

    # ---- Vérification ----
    if not api_key:
        raise RuntimeError("SOLEAS_API_KEY est vide.")
    if not private_key:
        raise RuntimeError("PRIVATE_SECRET_KEY est vide.")

    url = f"{SOLEAS_BASE_URL}/api/action/auth"

    # ---- Tentative 1 : clés dans les headers ----
    logger.info("--- TENTATIVE 1 : headers (x-api-key, x-private-key) ---")
    try:
        data = _essayer_auth(url, api_key, private_key, mode="headers")
    except requests.RequestException as e:
        logger.error(f"Tentative 1 échouée (réseau) : {e}")
        data = {"code": -1, "message": str(e)}

    token = data.get("access_token") or data.get("token") or data.get("data", {}).get("access_token")
    if token:
        logger.info(f"✅ Auth réussie via headers ! Token len={len(str(token))}")
        return token

    # Détecter un 401 applicatif (HTTP 200 mais code:401 dans le JSON)
    if data.get("code") == 401 or "Bad credentials" in str(data.get("message", "")):
        logger.warning("⚠️  Tentative 1 : 401 Bad credentials (headers). "
                       "L'API attend peut-être les clés dans le body JSON.")
    else:
        logger.warning(f"⚠️  Tentative 1 : pas de token. Réponse : {json.dumps(data)[:300]}")

    # ---- Tentative 2 : clés dans le body JSON ----
    logger.info("--- TENTATIVE 2 : body JSON (public_key, private_key) ---")
    try:
        data2 = _essayer_auth(url, api_key, private_key, mode="body")
    except requests.RequestException as e:
        logger.error(f"Tentative 2 échouée (réseau) : {e}")
        data2 = {"code": -1, "message": str(e)}

    token = data2.get("access_token") or data2.get("token") or data2.get("data", {}).get("access_token")
    if token:
        logger.info(f"✅ Auth réussie via body JSON ! Token len={len(str(token))}")
        return token

    if data2.get("code") == 401 or "Bad credentials" in str(data2.get("message", "")):
        logger.warning("⚠️  Tentative 2 : 401 Bad credentials (body JSON).")

    # ---- Échec des deux tentatives ----
    logger.critical(
        "AUTH ÉCHOUÉE après 2 tentatives — causes possibles :\n"
        "  1. Les identifiants SOLEAS_API_KEY / PRIVATE_SECRET_KEY sont incorrects.\n"
        "  2. Le service 'retrait' (withdraw) n'est pas activé sur le compte SoleasPay.\n"
        "  3. L'API /api/action/auth utilise des noms de champs différents\n"
        "     (pas public_key/private_key ni x-api-key/x-private-key).\n"
        "  4. L'URL SOLEAS_BASE_URL est incorrecte."
    )
    raise RuntimeError(
        "Impossible d'obtenir le token SoleasPay : "
        "échec de l'authentification après tentative headers + body JSON. "
        "Vérifiez les logs pour le détail."
    )


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