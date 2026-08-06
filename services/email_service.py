"""
Service Email — Resend (resend.com).
Utilisé pour l'envoi d'OTP, emails de bienvenue, réinitialisation, notifications.

Fonctions :
- send_otp_email(email, code, purpose) → envoie un email OTP HTML professionnel
- send_welcome_email(email, fullname) → email de bienvenue
- send_reset_confirmation_email(email, fullname) → confirmation de réinitialisation
- send_login_notification(email, fullname, ip) → notification de connexion
- _mask_key(key) → masque la clé API pour les logs
"""

import os
import logging
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# Logger
email_logger = logging.getLogger("email_service")
email_logger.setLevel(logging.INFO)

if not email_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] EMAIL | %(message)s"))
    email_logger.addHandler(handler)

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_API_URL = "https://api.resend.com/emails"
MAIL_FROM = os.getenv("MAIL_FROM", "TransAfrik <noreply@transafrik.org>")
PLATFORM_NAME = "TransAfrik"
PLATFORM_COLOR = "#F97316"        # Orange TransAfrik
PLATFORM_COLOR_DARK = "#EA580C"
PLATFORM_URL = "https://transafrik.org"
PLATFORM_LOGO_URL = "https://transafrik.org/static/img/trans1.png"  # À adapter si besoin


def _mask_key(key: str) -> str:
    """Masque une clé API pour le logging (affiche 6 premiers + 4 derniers)."""
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def _get_api_key() -> str:
    """Retourne la clé API Resend depuis les variables d'environnement."""
    return os.getenv("RESEND_API_KEY", "")


def _send_email(to_email: str, subject: str, html_body: str) -> dict:
    """Envoie un email via l'API Resend.

    Args:
        to_email: Adresse email du destinataire.
        subject: Sujet de l'email.
        html_body: Corps HTML de l'email.

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    api_key = _get_api_key()

    if not api_key:
        email_logger.error("Clé API Resend non configurée (RESEND_API_KEY).")
        return {
            "success": False,
            "message": "Configuration email manquante.",
            "raw_response": None,
        }

    payload = {
        "from": MAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    masked_key = _mask_key(api_key)
    email_logger.info(
        f"REQUÊTE Resend → "
        f"to={to_email} | "
        f"subject={subject} | "
        f"key={masked_key}"
    )

    start_time = time.time()
    resp = None

    try:
        resp = requests.post(
            RESEND_API_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )
        elapsed = time.time() - start_time
        status_code = resp.status_code

        email_logger.info(
            f"RÉPONSE Resend → "
            f"status={status_code} | "
            f"time={elapsed:.3f}s"
        )

        try:
            data = resp.json()
            email_logger.info(f"RÉPONSE JSON → {data}")
        except Exception:
            data = None
            email_logger.info(f"RÉPONSE TEXTE BRUT → {resp.text[:500]}")

        if status_code not in (200, 201, 202):
            email_logger.error(
                f"HTTP {status_code} → corps : {resp.text[:500]}"
            )
            return {
                "success": False,
                "message": f"Erreur du service email (HTTP {status_code}).",
                "raw_response": data,
                "http_status": status_code,
            }

        email_logger.info(f"EMAIL envoyé avec succès → {to_email}")
        return {
            "success": True,
            "message": "Email envoyé avec succès.",
            "raw_response": data,
            "http_status": status_code,
            "response_time": round(elapsed, 3),
        }

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        email_logger.error(f"Timeout envoi email → {to_email} | time={elapsed:.3f}s")
        return {
            "success": False,
            "message": "Délai d'attente dépassé lors de l'envoi de l'email.",
            "raw_response": None,
        }

    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_time
        email_logger.error(
            f"Erreur de connexion email → {to_email} | time={elapsed:.3f}s | {str(e)}"
        )
        return {
            "success": False,
            "message": f"Impossible de se connecter au service email : {str(e)}",
            "raw_response": None,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        email_logger.error(
            f"Erreur inattendue email → {to_email} | time={elapsed:.3f}s | {str(e)}"
        )
        if resp is not None:
            email_logger.error(f"Réponse brute du serveur : {resp.text[:500]}")
        return {
            "success": False,
            "message": f"Erreur inattendue : {str(e)}",
            "raw_response": str(e),
        }


# ================================================================
# TEMPLATES HTML
# ================================================================

def _base_template(content: str) -> str:
    """Template de base avec logo, couleurs TransAfrik, design glassmorphism."""
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{PLATFORM_NAME}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Outfit:wght@600;700;800&display=swap');
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
                color: #F1F5F9;
                line-height: 1.6;
                padding: 20px;
                min-height: 100vh;
                display: flex; align-items: center; justify-content: center;
            }}
            .email-container {{
                max-width: 520px;
                width: 100%;
                background: rgba(255,255,255,.04);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255,255,255,.08);
                border-radius: 24px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,.4);
            }}
            .email-header {{
                padding: 32px 32px 0;
                text-align: center;
            }}
            .email-logo {{
                font-family: 'Outfit', sans-serif;
                font-size: 28px;
                font-weight: 800;
                background: linear-gradient(135deg, {PLATFORM_COLOR}, #FFFFFF);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                margin-bottom: 8px;
            }}
            .email-divider {{
                width: 48px; height: 3px;
                background: linear-gradient(90deg, {PLATFORM_COLOR}, {PLATFORM_COLOR_DARK});
                border-radius: 2px;
                margin: 0 auto 28px;
            }}
            .email-body {{
                padding: 0 32px 32px;
            }}
            .email-title {{
                font-family: 'Outfit', sans-serif;
                font-size: 22px;
                font-weight: 700;
                text-align: center;
                margin-bottom: 12px;
            }}
            .email-text {{
                font-size: 14px;
                color: #CBD5E1;
                text-align: center;
                margin-bottom: 24px;
            }}
            .otp-box {{
                background: rgba(249,115,22,.1);
                border: 1px solid rgba(249,115,22,.25);
                border-radius: 16px;
                padding: 24px;
                text-align: center;
                margin-bottom: 24px;
            }}
            .otp-label {{
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: .1em;
                color: #94A3B8;
                margin-bottom: 8px;
            }}
            .otp-code {{
                font-family: 'Outfit', sans-serif;
                font-size: 42px;
                font-weight: 800;
                letter-spacing: 8px;
                color: {PLATFORM_COLOR};
                padding: 12px;
                background: rgba(249,115,22,.08);
                border-radius: 14px;
                display: inline-block;
                min-width: 240px;
                border: 1px dashed rgba(249,115,22,.3);
            }}
            .email-expire {{
                font-size: 12px;
                color: #64748B;
                text-align: center;
                margin-top: 12px;
            }}
            .email-btn {{
                display: block;
                width: 100%;
                padding: 14px 24px;
                background: linear-gradient(135deg, {PLATFORM_COLOR}, {PLATFORM_COLOR_DARK});
                color: #FFFFFF;
                text-align: center;
                text-decoration: none;
                font-weight: 700;
                font-size: 15px;
                border-radius: 14px;
                margin-bottom: 20px;
                box-shadow: 0 8px 24px rgba(249,115,22,.25);
            }}
            .email-footer {{
                text-align: center;
                padding: 20px 32px;
                border-top: 1px solid rgba(255,255,255,.06);
                font-size: 11px;
                color: #64748B;
            }}
            .email-footer a {{
                color: #94A3B8;
                text-decoration: none;
            }}
            .email-note {{
                font-size: 12px;
                color: #64748B;
                text-align: center;
                padding: 0 32px 24px;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <div class="email-logo">TransAfrik</div>
                <div class="email-divider"></div>
            </div>
            {content}
            <div class="email-footer">
                &copy; {PLATFORM_NAME} &mdash; Transferts d'argent en Afrique
            </div>
        </div>
    </body>
    </html>
    """


# ================================================================
# ENVOI OTP
# ================================================================

def send_otp_email(email: str, code: str, purpose: str) -> dict:
    """Envoie un email contenant un code OTP.

    Args:
        email: Adresse email du destinataire.
        code: Code OTP (6 chiffres).
        purpose: But de l'OTP (register | login | reset_password | change_phone).

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    purpose_labels = {
        "register": "inscription",
        "login": "connexion",
        "reset_password": "réinitialisation de mot de passe",
        "change_phone": "changement de numéro",
    }
    label = purpose_labels.get(purpose, "vérification")

    content = f"""
            <div class="email-body">
                <div class="email-title">Code de vérification</div>
                <div class="email-text">
                    Vous avez demandé un code de {label} sur {PLATFORM_NAME}.<br>
                    Utilisez le code ci-dessous pour continuer.
                </div>
                <div class="otp-box">
                    <div class="otp-label">Votre code de vérification</div>
                    <div class="otp-code">{code}</div>
                    <div class="email-expire">
                        Ce code expire dans <strong>5 minutes</strong>.
                    </div>
                </div>
                <div class="email-text email-expire">
                    Si vous n'êtes pas à l'origine de cette demande,<br>
                    ignorez simplement cet e-mail.
                </div>
            </div>
    """

    subject = "Code de vérification TransAfrik"
    html_body = _base_template(content)

    email_logger.info(f"OTP envoyé → {email} | purpose={purpose}")
    result = _send_email(email, subject, html_body)

    if result.get("success"):
        email_logger.info(f"Succès → {email} | purpose={purpose}")
    else:
        email_logger.error(f"Erreur → {email} | purpose={purpose} | {result.get('message')}")

    return result


# ================================================================
# EMAIL DE BIENVENUE
# ================================================================

def send_welcome_email(email: str, fullname: str) -> dict:
    """Envoie un email de bienvenue après création de compte.

    Args:
        email: Adresse email du destinataire.
        fullname: Nom complet de l'utilisateur.

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    first_name = fullname.split()[0] if fullname.strip() else fullname

    content = f"""
            <div class="email-body">
                <div class="email-title">Bienvenue sur TransAfrik, {first_name} !</div>
                <div class="email-text">
                    Votre compte a été créé avec succès.<br>
                    Vous pouvez désormais envoyer et recevoir de l'argent<br>
                    en toute sécurité à travers toute l'Afrique.
                </div>
                <a href="{PLATFORM_URL}/dashboard" class="email-btn">
                    Accéder à mon compte
                </a>
                <div class="email-text" style="font-size:13px;color:#94A3B8;">
                    Des questions ? Contactez notre support à<br>
                    <strong>support@transafrik.org</strong>
                </div>
            </div>
    """

    subject = f"Bienvenue sur TransAfrik, {first_name} !"
    html_body = _base_template(content)

    email_logger.info(f"Bienvenue envoyé → {email}")
    return _send_email(email, subject, html_body)


# ================================================================
# CONFIRMATION RÉINITIALISATION MOT DE PASSE
# ================================================================

def send_reset_confirmation_email(email: str, fullname: str) -> dict:
    """Envoie un email de confirmation après réinitialisation de mot de passe.

    Args:
        email: Adresse email du destinataire.
        fullname: Nom complet de l'utilisateur.

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    first_name = fullname.split()[0] if fullname.strip() else fullname

    content = f"""
            <div class="email-body">
                <div class="email-title">Mot de passe modifié</div>
                <div class="email-text">
                    Bonjour {first_name},<br>
                    Votre mot de passe TransAfrik a été modifié avec succès.
                </div>
                <div class="email-text" style="font-size:12px;color:#64748B;">
                    Si vous n'êtes pas à l'origine de cette modification,<br>
                    contactez immédiatement notre support à<br>
                    <strong>support@transafrik.org</strong>
                </div>
            </div>
    """

    subject = "Votre mot de passe TransAfrik a été modifié"
    html_body = _base_template(content)

    email_logger.info(f"Confirmation reset envoyé → {email}")
    return _send_email(email, subject, html_body)


# ================================================================
# NOTIFICATION DE CONNEXION
# ================================================================

def send_login_notification(email: str, fullname: str, ip: str = "") -> dict:
    """Envoie une notification de nouvelle connexion.

    Args:
        email: Adresse email du destinataire.
        fullname: Nom complet de l'utilisateur.
        ip: Adresse IP de la connexion (optionnelle).

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    first_name = fullname.split()[0] if fullname.strip() else fullname

    ip_info = f"<br>Adresse IP : <strong>{ip}</strong>" if ip else ""

    content = f"""
            <div class="email-body">
                <div class="email-title">Nouvelle connexion détectée</div>
                <div class="email-text">
                    Bonjour {first_name},<br>
                    Une nouvelle connexion à votre compte TransAfrik<br>
                    vient d'être effectuée.{ip_info}
                </div>
                <div class="email-text" style="font-size:12px;color:#64748B;">
                    Si vous n'êtes pas à l'origine de cette connexion,<br>
                    modifiez immédiatement votre mot de passe<br>
                    et contactez notre support.
                </div>
            </div>
    """

    subject = "Nouvelle connexion à votre compte TransAfrik"
    html_body = _base_template(content)

    email_logger.info(f"Notification connexion envoyée → {email}")
    return _send_email(email, subject, html_body)


# ================================================================
# CONFIRMATION DE DEPOT
# ================================================================

def send_deposit_email(email: str, fullname: str, amount: float,
                       currency: str = "XOF", reference: str = "") -> dict:
    """Envoie un email de confirmation de depot.

    Args:
        email:     Adresse email du destinataire.
        fullname:  Nom complet de l'utilisateur.
        amount:    Montant du depot.
        currency:  Devise (defaut XOF).
        reference: Reference de la transaction.

    Returns:
        {"success": True/False, "message": "...", "raw_response": {...}}
    """
    first_name = fullname.split()[0] if fullname.strip() else fullname
    from datetime import datetime
    date_str = datetime.utcnow().strftime("%d/%m/%Y a %H:%M")

    ref_line = f"<br>Reference : <strong>{reference}</strong>" if reference else ""

    content = f"""
            <div class="email-body">
                <div class="email-title">Depot confirme</div>
                <div class="email-text">
                    Bonjour {first_name},<br><br>
                    Votre depot a ete credite avec succes sur votre compte TransAfrik.<br><br>
                    <strong>Montant :</strong> {amount:,.0f} {currency}<br>
                    <strong>Date :</strong> {date_str}{ref_line}
                </div>
                <div class="email-text" style="font-size:12px;color:#64748B;">
                    Vous pouvez consulter votre solde et l'historique<br>
                    de vos transactions dans votre espace TransAfrik.
                </div>
            </div>
    """

    subject = f"Depot confirme - {amount:,.0f} {currency}"
    html_body = _base_template(content)

    email_logger.info(f"Confirmation depot envoyee -> {email} | ref={reference}")
    return _send_email(email, subject, html_body)
