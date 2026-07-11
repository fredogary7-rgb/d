#!/usr/bin/env python3
"""
Script de test indépendant pour l'envoi SMS via SoSMS (mysoleas.com).

Usage :
    python test_sms.py               # envoie un SMS de test au numéro par défaut
    python test_sms.py 22871339325   # envoie un SMS au numéro spécifié

Ne dépend PAS de Flask ni du système OTP.
Teste directement l'API SoSMS.
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ───────────────────────────────────────────
SOSMS_BASE_URL = os.getenv("SOSMS_BASE_URL", "https://mysoleas.com")
SOSMS_API_KEY = os.getenv("SOSMS_API_KEY", "")
SOSMS_SEND_URL = f"{SOSMS_BASE_URL}/v2/sms/add"

# Numéro de test par défaut (Togo)
DEFAULT_TEST_PHONE = "22871339325"
MAX_SMS_LENGTH = 160


def mask_key(key: str) -> str:
    """Masque une clé API pour l'affichage."""
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def normalize_phone(phone: str) -> str:
    """Nettoie un numéro : garde uniquement les chiffres."""
    import re
    return re.sub(r"[^\d]", "", phone.strip())


def main():
    # ── Récupérer le numéro ──────────────────────────────────
    if len(sys.argv) > 1:
        phone = sys.argv[1]
    else:
        phone = DEFAULT_TEST_PHONE

    phone_clean = normalize_phone(phone)

    # ── Construire le message ─────────────────────────────────
    message = "TransAfrik Test - Ceci est un SMS de test envoye depuis test_sms.py"
    if len(message) > MAX_SMS_LENGTH:
        print(f"[WARN] Message trop long ({len(message)} car.), tronqué à {MAX_SMS_LENGTH}")
        message = message[:MAX_SMS_LENGTH]

    # ── Vérifications préalables ──────────────────────────────
    print("=" * 60)
    print("TEST SMS — SoSMS API")
    print("=" * 60)

    print(f"\n1. Vérification de la clé API...")
    if not SOSMS_API_KEY:
        print("   [FAIL] SOSMS_API_KEY est vide ou non définie dans .env")
        sys.exit(1)
    print(f"   [OK]   Clé présente : {mask_key(SOSMS_API_KEY)}")

    print(f"\n2. Numéro de téléphone...")
    print(f"   Brut    : {phone}")
    print(f"   Nettoyé : {phone_clean}")
    print(f"   Taille  : {len(phone_clean)} chiffres")

    print(f"\n3. Message...")
    print(f"   Contenu : {repr(message)}")
    print(f"   Taille  : {len(message)} caractères")
    if len(message) > MAX_SMS_LENGTH:
        print(f"   [WARN]  Dépasse {MAX_SMS_LENGTH} car. !")

    # ── Paramètres de la requête ──────────────────────────────
    payload = {
        "key": SOSMS_API_KEY,
        "contact": phone_clean,
        "message": message,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    print(f"\n4. Requête...")
    print(f"   URL        : {SOSMS_SEND_URL}")
    print(f"   Méthode    : POST")
    print(f"   Content-Type: application/x-www-form-urlencoded")
    print(f"   Paramètres  :")
    print(f"     - key     = {mask_key(payload['key'])}")
    print(f"     - contact = {payload['contact']}")
    print(f"     - message = {repr(payload['message'])}")

    # ── Envoyer la requête ────────────────────────────────────
    print(f"\n5. Envoi du SMS...")
    start_time = time.time()

    try:
        resp = requests.post(
            SOSMS_SEND_URL,
            data=payload,
            headers=headers,
            timeout=15,
        )
        elapsed = time.time() - start_time

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"   [FAIL] Timeout après {elapsed:.3f}s")
        sys.exit(1)

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_time
        print(f"   [FAIL] Erreur de connexion : {e}")
        sys.exit(1)

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   [FAIL] Erreur inattendue : {e}")
        sys.exit(1)

    # ── Afficher la réponse ───────────────────────────────────
    status_code = resp.status_code

    print(f"\n6. Réponse HTTP...")
    print(f"   Status       : {status_code} ({'OK' if status_code == 200 else 'ERREUR'})")
    print(f"   Temps        : {elapsed:.3f}s")
    print(f"   Content-Type : {resp.headers.get('Content-Type', 'N/A')}")
    print(f"   Taille corps : {len(resp.text)} octets")

    print(f"\n7. Corps de la réponse...")

    # Essayer de parser en JSON
    try:
        data = resp.json()
        print(f"   Format JSON détecté :")
        print(f"   {json.dumps(data, indent=4, ensure_ascii=False)}")

        # Analyse rapide
        if data.get("code") == 0 or data.get("success") is True:
            print(f"\n   [SUCCESS] Le SMS semble avoir été accepté !")
        elif data.get("code") == 1 or data.get("success") is False:
            print(f"\n   [FAIL] L'API a retourné une erreur.")
            if "message" in data:
                print(f"   Message : {data['message']}")
        else:
            print(f"\n   [INFO] Statut inconnu, vérifier la réponse ci-dessus.")

    except (json.JSONDecodeError, ValueError):
        # Réponse non-JSON
        print(f"   Format TEXTE :")
        text_preview = resp.text[:500]
        print(f"   {text_preview}")

        if status_code == 200:
            print(f"\n   [SUCCESS] HTTP 200 reçu (probablement OK).")
        else:
            print(f"\n   [FAIL] HTTP {status_code}.")
            # Afficher le texte complet si < 2000 car.
            if len(resp.text) <= 2000:
                print(f"\n   CORPS COMPLET ({len(resp.text)} car.) :")
                print(f"   {resp.text}")
            else:
                print(f"\n   PREMIERS 500 CAR. : {resp.text[:500]}")
                print(f"   DERNIERS 500 CAR. : {resp.text[-500:]}")

    # ── Résumé ────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"RÉSUMÉ :")
    print(f"  URL      : {SOSMS_SEND_URL}")
    print(f"  Contact  : {phone_clean}")
    print(f"  HTTP     : {status_code}")
    print(f"  Temps    : {elapsed:.3f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()