"""
Service SMS — SoSMS (Soleas SMS) via mysoleas.com.

Fonctions :
- send_sms(phone, message) : envoie un SMS via l'API SoSMS
- refresh_api_key()       : recharge la clé API depuis les variables d'environnement
- format_phone(phone)     : normalise un numéro au format international
"""

import os
import logging
import re
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


def get_api_key() -> str:
    """Retourne la clé API SoSMS depuis les variables d'environnement.

    Returns:
        La clé API (str), ou chaîne vide si non configurée.
    """
    return os.getenv("SOSMS_API_KEY", "")


def refresh_api_key() -> str:
    """Recharge la clé API depuis les variables d'environnement (utile si maj runtime).

    Returns:
        La nouvelle clé API.
    """
    global SOSMS_API_KEY
    SOSMS_API_KEY = os.getenv("SOSMS_API_KEY", "")
    sms_logger.info("Clé API SoSMS rechargée.")
    return SOSMS_API_KEY


def format_phone(phone: str) -> str:
    """Normalise un numéro de téléphone au format international (sans le +).

    Exemples :
        '+229 97 00 00 00' → '22997000000'
        '229 97 00 00 00'  → '22997000000'
        '97 00 00 00'       → '22997000000' (si pays par défaut = BJ)
        '0700000000'        → '2250700000000' (si Côte d'Ivoire)

    Args:
        phone: Numéro brut fourni par l'utilisateur.

    Returns:
        Numéro normalisé (chaîne de chiffres uniquement, sans '+').
    """
    # Nettoyer tous les caractères non numériques sauf le '+'
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # Retirer le '+' si présent
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    sms_logger.debug(f"format_phone: '{phone}' → '{cleaned}'")
    return cleaned


def send_sms(phone: str, message: str) -> dict:
    """Envoie un SMS via l'API SoSMS (mysoleas.com).

    POST https://mysoleas.com/v2/sms/add
    Body: { "contact": "22997000000", "key": "API_KEY", "message": "..." }

    Args:
        phone: Numéro du destinataire (format international sans '+').
        message: Contenu du SMS (max 160 caractères recommandé).

    Returns:
        Dictionnaire de réponse :
            {
                "success": True/False,
                "message": "SMS envoyé avec succès" / "Erreur: ...",
                "raw_response": {...}  # réponse brute de l'API
            }
    """
    api_key = get_api_key()

    if not api_key:
        sms_logger.error("Clé API SoSMS non configurée (SOSMS_API_KEY).")
        return {
            "success": False,
            "message": "Configuration SMS manquante.",
            "raw_response": None,
        }

    phone_clean = format_phone(phone)

    payload = {
        "contact": phone_clean,
        "key": api_key,
        "message": message,
    }

    sms_logger.info(
        f"Envoi SMS → {phone_clean} | "
        f"message={message[:50]}{'...' if len(message) > 50 else ''}"
    )

    try:
        resp = requests.post(
            SOSMS_SEND_URL,
            json=payload,
            timeout=15,
            headers={"Content-Type": "application/json"},
        )

        resp.raise_for_status()
        data = resp.json()

        sms_logger.info(
            f"SMS envoyé avec succès → {phone_clean} | "
            f"status={resp.status_code} | response={data}"
        )

        return {
            "success": True,
            "message": "SMS envoyé avec succès.",
            "raw_response": data,
        }

    except requests.exceptions.Timeout:
        sms_logger.error(f"Timeout envoi SMS → {phone_clean}")
        return {
            "success": False,
            "message": "Délai d'attente dépassé lors de l'envoi du SMS.",
            "raw_response": None,
        }

    except requests.exceptions.ConnectionError:
        sms_logger.error(f"Erreur de connexion SMS → {phone_clean}")
        return {
            "success": False,
            "message": "Impossible de se connecter au service SMS.",
            "raw_response": None,
        }

    except requests.exceptions.HTTPError as e:
        sms_logger.error(
            f"Erreur HTTP SMS → {phone_clean} | "
            f"status={resp.status_code} | body={resp.text[:200]}"
        )
        return {
            "success": False,
            "message": f"Erreur du service SMS (HTTP {resp.status_code}).",
            "raw_response": resp.text[:200],
        }

    except Exception as e:
        sms_logger.error(
            f"Erreur inattendue SMS → {phone_clean} | {str(e)}"
        )
        return {
            "success": False,
            "message": f"Erreur inattendue : {str(e)}",
            "raw_response": None,
        }