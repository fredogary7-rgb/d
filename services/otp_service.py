"""
Service OTP - Generation et validation de codes a usage unique.

Fonctions :
- generate_otp()           - code 6 chiffres (crypto-safe)
- create_otp(phone, purpose) - cree un OTP en base et retourne le code
- verify_otp(phone, code, purpose) - verifie et invalide le code OTP
- resend_otp(phone)        - renvoie un OTP (verifie le delai de 60s)
- delete_expired_otps()    - nettoie les OTP expires
"""

import secrets
import logging
from datetime import datetime, timedelta, timezone
from models import db, OtpCode

# Logger
otp_logger = logging.getLogger("otp_service")
otp_logger.setLevel(logging.INFO)

if not otp_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(asctime)s] OTP | %(message)s"))
    otp_logger.addHandler(handler)

# Constantes
OTP_LENGTH = 6
OTP_VALIDITY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_PER_HOUR = 5


def generate_otp(length: int = OTP_LENGTH) -> str:
    """Genere un code OTP cryptographiquement securise (6 chiffres)."""
    code = "".join(str(secrets.randbelow(10)) for _ in range(length))
    otp_logger.debug(f"Code OTP genere : {code}")
    return code


def create_otp(phone: str, purpose: str) -> dict:
    """Cree un nouvel OTP pour un telephone donne (avec anti-abus).

    Returns:
        {"success": True, "code": "482913", "otp_id": 123}
        ou {"success": False, "error": "..."}
    """
    # Anti-abus : delai 60s entre deux envois
    recent_otp = OtpCode.query.filter_by(phone=phone, is_verified=False).order_by(
        OtpCode.created_at.desc()
    ).first()

    if recent_otp:
        elapsed = (datetime.now(timezone.utc) - recent_otp.created_at.replace(
            tzinfo=timezone.utc
        )).total_seconds()

        if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
            wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
            otp_logger.warning(f"Anti-spam : renvoi bloque pour {phone} - attendre {wait}s")
            return {
                "success": False,
                "error": f"Veuillez attendre {wait} secondes avant de renvoyer un code.",
            }

    # Anti-abus : max 5 OTP par heure
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    hourly_count = OtpCode.query.filter(
        OtpCode.phone == phone,
        OtpCode.created_at >= one_hour_ago,
    ).count()

    if hourly_count >= OTP_MAX_PER_HOUR:
        otp_logger.warning(f"Anti-abus : trop d'OTP pour {phone} ({hourly_count}/h)")
        return {
            "success": False,
            "error": "Trop de tentatives. Veuillez reessayer dans une heure.",
        }

    # Supprimer les anciens OTP non verifies
    OtpCode.query.filter(
        OtpCode.phone == phone,
        OtpCode.is_verified == False,
    ).delete()

    # Creer le nouveau code
    code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES)

    otp = OtpCode(
        phone=phone,
        code=code,
        purpose=purpose,
        expires_at=expires_at,
        attempts=0,
        is_verified=False,
    )
    db.session.add(otp)
    db.session.commit()

    otp_logger.info(
        f"OTP cree - phone={phone} | purpose={purpose} | "
        f"id={otp.id} | expires={expires_at.isoformat()}"
    )

    return {"success": True, "code": code, "otp_id": otp.id}


def verify_otp(phone: str, code: str, purpose: str) -> dict:
    """Verifie un code OTP saisi par l'utilisateur.

    Returns:
        {"success": True} ou {"success": False, "error": "...", "attempts_remaining": 2}
    """
    otp = OtpCode.query.filter_by(
        phone=phone, purpose=purpose, is_verified=False,
    ).order_by(OtpCode.created_at.desc()).first()

    if not otp:
        otp_logger.warning(f"OTP introuvable pour {phone} / {purpose}")
        return {
            "success": False,
            "error": "Aucun code de verification trouve. Veuillez en demander un nouveau.",
        }

    if otp.is_expired:
        otp_logger.warning(f"OTP expire - phone={phone} | id={otp.id}")
        return {
            "success": False,
            "error": "Le code a expire. Veuillez en demander un nouveau.",
        }

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        otp_logger.warning(f"OTP bloque - phone={phone} | id={otp.id} | attempts={otp.attempts}")
        otp.is_verified = True
        db.session.commit()
        return {
            "success": False,
            "error": "Trop de tentatives. Veuillez demander un nouveau code.",
        }

    otp.attempts += 1
    db.session.commit()

    if otp.code != code.strip():
        remaining = OTP_MAX_ATTEMPTS - otp.attempts
        otp_logger.warning(
            f"Code OTP invalide - phone={phone} | id={otp.id} | "
            f"attempt={otp.attempts}/{OTP_MAX_ATTEMPTS} | restant={remaining}"
        )
        return {
            "success": False,
            "error": f"Code incorrect. Il vous reste {remaining} tentative(s).",
            "attempts_remaining": remaining,
        }

    otp.is_verified = True
    db.session.commit()

    otp_logger.info(f"OTP valide - phone={phone} | id={otp.id} | purpose={purpose}")
    return {"success": True, "message": "Code verifie avec succes."}


def resend_otp(phone: str) -> dict:
    """Renvoie un OTP (recupere le purpose depuis le dernier OTP)."""
    last_otp = OtpCode.query.filter_by(phone=phone).order_by(
        OtpCode.created_at.desc()
    ).first()

    if not last_otp:
        return {
            "success": False,
            "error": "Aucun code a renvoyer. Veuillez recommencer.",
        }

    return create_otp(phone, last_otp.purpose)


def delete_expired_otps() -> int:
    """Supprime tous les OTP expires. Retourne le nombre supprime."""
    deleted = OtpCode.query.filter(
        OtpCode.expires_at < datetime.now(timezone.utc)
    ).delete()
    db.session.commit()
    if deleted > 0:
        otp_logger.info(f"Nettoyage OTP : {deleted} code(s) expire(s) supprime(s).")
    return deleted