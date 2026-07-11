"""
Service SMS — SoSMS (Soleas SMS) via mysoleas.com.

Fonctions :
- send_sms(phone, message) : envoie un SMS via l'API SoSMS
- refresh_api_key()       : recharge la clé API depuis les variables d'environnement
- normalize_phone(phone)  : normalise un numéro pour l'API SoSMS
- format_phone(phone)     : alias rétrocompatible de normalize_phone
"""

import os
import logging
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Logger
sms_logger = logging.getLogger("sms_service")
sms_logger.setLevel(logging.INFO)

if not sms_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] SMS | %(message)s"))
    sms_logger.addHandler(handler)

# Configuration
SOSMS_BASE_URL = os.getenv("SOSMS_BASE_URL", "https://mysoleas.com")
SOSMS_API_KEY = os.getenv("SOSMS_API_KEY", "")
SOSMS_SEND_URL = f"{SOSMS_BASE_URL}/v2/sms/add"

# Codes pays africains supportés
AFRICAN_COUNTRY_CODES = {
    "228": "TG",  # Togo
    "229": "BJ",  # Bénin
    "237": "CM",  # Cameroun
    "225": "CI",  # Côte d'Ivoire
    "226": "BF",  # Burkina Faso
    "242": "CG",  # Congo
    "243": "CD",  # RD Congo
    "241": "GA",  # Gabon
    "256": "UG",  # Ouganda
    "260": "ZM",  # Zambie
    "221": "SN",  # Sénégal
}


def get_api_key() -> str:
    """Retourne la clé API SoSMS depuis les variables d'environnement.
    """
    return os.getenv("SOSMS_API_KEY", "")


def refresh_api_key() -> str:
    """Recharge la clé API depuis les variables d'environnement (utile si maj runtime).
    """
    global SOSMS_API_KEY
    SOSMS_API_KEY = os.getenv("SOSMS_API_KEY", "")
    sms_logger.info("Clé API SoSMS rechargée.")
    return SOSMS_API_KEY


def normalize_phone(phone: str) -> str:
    """Normalise un numéro de téléphone pour l'API SoSMS.

    Règles :
    - Supprime tous les caractères non numériques
    - Si le numéro commence par un indicatif africain connu (228, 229, etc.),
      on le garde tel quel (format international sans +)
    - Sinon, on le laisse tel quel (format local de l'opérateur)

    Exemples :
        '+228 71 33 93 25'  → '22871339325'
        '71339325'           → '71339325'
        '22871339325'        → '22871339325'
        '+229 97 00 00 00'   → '22997000000'

    Args:
        phone: Numéro brut fourni par l'utilisateur.

    Returns:
        Numéro normalisé (chaîne de chiffres uniquement, sans '+').
    """
    cleaned = re.sub(r"[^\d]", "", phone.strip())

    sms_logger.debug(f"normalize_phone: '{phone}' → '{cleaned}'")
    return cleaned


def format_phone(phone: str) -> str:
    """Alias rétrocompatible de normalize_phone."""
    return normalize_phone(phone)


def _mask_key(key: str) -> str:
    """Masque une clé API pour le logging (affiche 6 premiers + 4 derniers)."""
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def send_sms(phone: str, message: str) -> dict:
    """Envoie un SMS via l'API SoSMS (mysoleas.com).

    Documentation : POST https://mysoleas.com/v2/sms/add
    Content-Type: application/x-www-form-urlencoded
    Paramètres : key, contact, message

    Args:
        phone: Numéro du destinataire.
        message: Contenu du SMS (max 160 caractères recommandé).

    Returns:
        {
            "success": True/False,
            "message": "...",
            "raw_response": {...}
        }
    """
    api_key = get_api_key()

    # 5. Vérifier que la clé API est présente et non vide
    if not api_key:
        sms_logger.error("Clé API SoSMS non configurée (SOSMS_API_KEY).")
        return {
            "success": False,
            "message": "Configuration SMS manquante.",
            "raw_response": None,
        }

    # 4. Normaliser le numéro
    phone_clean = normalize_phone(phone)

    # 5. Vérifier la taille du message (max 160 car.)
    MAX_SMS_LENGTH = 160
    if len(message) > MAX_SMS_LENGTH:
        sms_logger.warning(
            f"Message SMS trop long ({len(message)} car.), "
            f"tronqué à {MAX_SMS_LENGTH} car."
        )
        message = message[:MAX_SMS_LENGTH]

    # Form-encoded : les paramètres comme un dict
    payload = {
        "key": api_key,
        "contact": phone_clean,
        "message": message,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # 1. Logger la requête (sans la clé API complète)
    masked_key = _mask_key(api_key)
    sms_logger.info(
        f"REQUÊTE SoSMS → "
        f"URL={SOSMS_SEND_URL} | "
        f"method=POST | "
        f"Content-Type=application/x-www-form-urlencoded | "
        f"contact={phone_clean} | "
        f"key={masked_key} | "
        f"message_len={len(message)} | "
        f"message_preview={repr(message[:50])}"
    )

    start_time = time.time()
    resp = None
    status_code = None

    try:
        # 7. Envoyer en form-encoded (data=, pas json=)
        resp = requests.post(
            SOSMS_SEND_URL,
            data=payload,
            timeout=15,
            headers=headers,
        )
        elapsed = time.time() - start_time
        status_code = resp.status_code

        # 2. Logger la réponse complète
        sms_logger.info(
            f"RÉPONSE SoSMS → "
            f"status={status_code} | "
            f"time={elapsed:.3f}s | "
            f"content_type={resp.headers.get('Content-Type', 'N/A')} | "
            f"body_len={len(resp.text)}"
        )

        # Tenter de parser le JSON
        try:
            data = resp.json()
            sms_logger.info(f"RÉPONSE JSON → {data}")
        except Exception:
            data = None
            sms_logger.info(
                f"RÉPONSE TEXTE BRUT → {resp.text[:500]}"
            )

        # 7. Si HTTP != 200, logger le texte complet
        if status_code != 200:
            sms_logger.error(
                f"HTTP {status_code} → "
                f"corps complet ({len(resp.text)} car.) : {resp.text}"
            )
            return {
                "success": False,
                "message": f"Erreur du service SMS (HTTP {status_code}) : {resp.text[:300]}",
                "raw_response": data if data else resp.text[:500],
                "http_status": status_code,
            }

        sms_logger.info(
            f"SMS envoyé avec succès → {phone_clean} | "
            f"status={status_code} | time={elapsed:.3f}s"
        )

        return {
            "success": True,
            "message": "SMS envoyé avec succès.",
            "raw_response": data,
            "http_status": status_code,
            "response_time": round(elapsed, 3),
        }

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        sms_logger.error(f"Timeout envoi SMS → {phone_clean} | time={elapsed:.3f}s")
        return {
            "success": False,
            "message": "Délai d'attente dépassé lors de l'envoi du SMS.",
            "raw_response": None,
        }

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_time
        sms_logger.error(
            f"Erreur de connexion SMS → {phone_clean} | time={elapsed:.3f}s | {str(e)}"
        )
        return {
            "success": False,
            "message": f"Impossible de se connecter au service SMS : {str(e)}",
            "raw_response": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        sms_logger.error(
            f"Erreur inattendue SMS → {phone_clean} | time={elapsed:.3f}s | {str(e)}"
        )
        # 7. Logger le texte brut si disponible
        if resp is not None:
            sms_logger.error(f"Réponse brute du serveur : {resp.text[:500]}")
        return {
            "success": False,
            "message": f"Erreur inattendue : {str(e)}",
            "raw_response": str(e),
        }
