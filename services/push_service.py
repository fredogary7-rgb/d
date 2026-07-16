"""
Web Push Service — TransAfrik
Production-ready Web Push notifications via pywebpush + VAPID.
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional

from flask import current_app
from pywebpush import webpush, WebPushException
from models import db, PushSubscription, User

# Logger
push_logger = logging.getLogger("push_service")
push_logger.setLevel(logging.INFO)
if not push_logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] PUSH | %(message)s"))
    push_logger.addHandler(h)


def _get_vapid_claims():
    """Retourne les claims VAPID : subject = mailto:support@transafrik.com."""
    return {"sub": "mailto:support@transafrik.com"}


def _get_vapid_private_key() -> str:
    """Lit la clé privée VAPID depuis l'environnement, avec fallback config admin."""
    from admin.models import SystemConfig
    key = os.getenv("VAPID_PRIVATE_KEY") or SystemConfig.get("vapid_private_key", "")
    return key.strip()


def _get_vapid_public_key() -> str:
    """Lit la clé publique VAPID."""
    from admin.models import SystemConfig
    key = os.getenv("VAPID_PUBLIC_KEY") or SystemConfig.get("vapid_public_key", "")
    return key.strip()


def _detect_platform(user_agent: str) -> str:
    """Détecte la plateforme (android/ios/macos/linux/windows) depuis l'User-Agent."""
    ua = user_agent.lower() if user_agent else ""
    if "android" in ua:
        return "android"
    if "iphone" in ua or "ipad" in ua or "ipod" in ua:
        return "ios"
    if "mac os" in ua or "macintosh" in ua:
        return "macos"
    if "windows" in ua:
        return "windows"
    if "linux" in ua:
        return "linux"
    return "unknown"


def _detect_browser(user_agent: str) -> str:
    """Détecte le navigateur depuis l'User-Agent."""
    ua = user_agent.lower() if user_agent else ""
    if "edg/" in ua or "edge/" in ua:
        return "edge"
    if "chrome/" in ua and "crios/" not in ua:
        return "chrome"
    if "firefox/" in ua or "fxios/" in ua:
        return "firefox"
    if "safari/" in ua and "chrome/" not in ua:
        return "safari"
    if "opera/" in ua or "opr/" in ua:
        return "opera"
    return "unknown"


def _clean_device_name(user_agent: str, browser: str) -> str:
    """Extrait un nom d'appareil lisible depuis l'User-Agent."""
    ua = user_agent if user_agent else ""
    parts = ua.split(")")
    if len(parts) >= 1:
        first = parts[0].split("(")
        os_info = first[-1].strip() if len(first) > 1 else ""
        # Nettoyer
        os_info = os_info.replace("AppleWebKit/537.36", "").replace("KHTML, like Gecko", "").strip()
        if os_info:
            return f"{os_info} - {browser}"
    return f"Unknown - {browser}"


# ───────────────────────────────────────────────
#  Gestion des abonnements
# ───────────────────────────────────────────────

def save_subscription(user_id: int, subscription_data: dict, user_agent: str = "") -> dict:
    """Enregistre ou met à jour un abonnement Push.

    Args:
        user_id: ID de l'utilisateur.
        subscription_data: Objet PushSubscription du navigateur (endpoint, keys).
        user_agent: User-Agent du navigateur.

    Returns:
        {"success": True, "subscription_id": 42}
        ou {"success": False, "error": "..."}
    """
    endpoint = subscription_data.get("endpoint", "").strip()
    keys = subscription_data.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")

    if not endpoint or not p256dh or not auth:
        push_logger.warning(f"Données d'abonnement incomplètes pour user_id={user_id}")
        return {"success": False, "error": "Données d'abonnement incomplètes."}

    platform = _detect_platform(user_agent)
    browser = _detect_browser(user_agent)
    device_name = _clean_device_name(user_agent, browser)

    # Vérifier si l'abonnement existe déjà (même endpoint pour ce user)
    existing = PushSubscription.query.filter_by(
        user_id=user_id, endpoint=endpoint
    ).first()

    if existing:
        # Mise à jour
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent[:500] if user_agent else None
        existing.platform = platform
        existing.browser = browser
        existing.device_name = device_name
        existing.updated_at = datetime.utcnow()
        existing.last_seen = datetime.utcnow()
        db.session.commit()
        push_logger.info(
            f"SUBSCRIPTION | Mise à jour existante id={existing.id} "
            f"user={user_id} platform={platform} browser={browser}"
        )
        return {"success": True, "subscription_id": existing.id, "updated": True}
    else:
        # Nouvel abonnement
        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent[:500] if user_agent else None,
            platform=platform,
            browser=browser,
            device_name=device_name,
        )
        db.session.add(sub)
        db.session.commit()
        push_logger.info(
            f"SUBSCRIPTION | Nouvelle enregistrée id={sub.id} "
            f"user={user_id} platform={platform} browser={browser}"
        )
        return {"success": True, "subscription_id": sub.id, "created": True}


def remove_subscription(user_id: int, endpoint: str) -> dict:
    """Supprime un abonnement Push.

    Args:
        user_id: ID de l'utilisateur.
        endpoint: Endpoint Push à supprimer.

    Returns:
        {"success": True, "deleted": True}
    """
    sub = PushSubscription.query.filter_by(
        user_id=user_id, endpoint=endpoint
    ).first()

    if sub:
        db.session.delete(sub)
        db.session.commit()
        push_logger.info(
            f"UNSUBSCRIPTION | Supprimée id={sub.id} user={user_id} platform={sub.platform}"
        )
        return {"success": True, "deleted": True}

    push_logger.info(
        f"UNSUBSCRIPTION | Non trouvée user={user_id} endpoint={endpoint[:60]}..."
    )
    return {"success": True, "deleted": False}


def remove_subscription_by_id(subscription_id: int) -> dict:
    """Supprime un abonnement par son ID (utilisé après erreur 404/410)."""
    sub = PushSubscription.query.get(subscription_id)
    if sub:
        db.session.delete(sub)
        db.session.commit()
        push_logger.info(
            f"SUPPRESSION | Abonnement invalide supprimé id={subscription_id} "
            f"user={sub.user_id} platform={sub.platform}"
        )
        return {"success": True, "deleted": True}
    return {"success": False, "deleted": False}


def get_user_subscriptions(user_id: int) -> list:
    """Retourne la liste des abonnements d'un utilisateur."""
    subs = PushSubscription.query.filter_by(user_id=user_id).order_by(
        PushSubscription.last_seen.desc()
    ).all()
    return [s.to_dict() for s in subs]


def get_all_active_subscriptions() -> list:
    """Retourne TOUS les abonnements actifs pour un envoi global."""
    return PushSubscription.query.order_by(PushSubscription.id).all()


def get_subscription_stats() -> dict:
    """Statistiques des abonnements Push."""
    total = PushSubscription.query.count()
    per_platform = db.session.query(
        PushSubscription.platform,
        db.func.count(PushSubscription.id)
    ).group_by(PushSubscription.platform).all()

    per_browser = db.session.query(
        PushSubscription.browser,
        db.func.count(PushSubscription.id)
    ).group_by(PushSubscription.browser).all()

    stats = {
        "total": total,
        "platforms": {p: c for p, c in per_platform if p},
        "browsers": {b: c for b, c in per_browser if b},
    }
    return stats


# ───────────────────────────────────────────────
#  Envoi de notification
# ───────────────────────────────────────────────

def send_push_notification(
    subscription_id: int,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/static/img/icons/icon-192x192.png",
    badge: str = "/static/img/icons/icon-72x72.png",
    tag: str = "transafrik",
    data: Optional[dict] = None,
    actions: Optional[list] = None,
    require_interaction: bool = False,
    ttl: int = 2419200,  # 4 semaines
) -> dict:
    """Envoie une notification Push à un abonnement spécifique.

    Returns:
        {"success": True, "message": "..."} ou {"success": False, "error": "...", "status_code": int}
    """
    sub = PushSubscription.query.get(subscription_id)
    if not sub:
        return {"success": False, "error": "Abonnement introuvable."}

    return _send_to_subscription(sub, title, body, url, icon, badge, tag, data, actions, require_interaction, ttl)


def send_push_to_all(
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/static/img/icons/icon-192x192.png",
    badge: str = "/static/img/icons/icon-72x72.png",
    tag: str = "transafrik-broadcast",
    data: Optional[dict] = None,
    actions: Optional[list] = None,
    require_interaction: bool = False,
) -> dict:
    """Envoie une notification Push à TOUS les abonnements actifs.

    Returns:
        {"success": True, "sent": 10, "failed": 2, "cleaned": 3, "details": [...]}
    """
    subs = get_all_active_subscriptions()
    results = {"success": True, "sent": 0, "failed": 0, "cleaned": 0, "details": []}

    for sub in subs:
        r = _send_to_subscription(sub, title, body, url, icon, badge, tag, data, actions, require_interaction)
        if r.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
            if r.get("status_code") in (404, 410):
                # Abonnement invalide — le supprimer
                remove_subscription_by_id(sub.id)
                results["cleaned"] += 1
                push_logger.info(
                    f"ERREUR {r.get('status_code')} | Suppression abonnement invalide "
                    f"id={sub.id} user={sub.user_id}"
                )
            results["details"].append({
                "subscription_id": sub.id,
                "user_id": sub.user_id,
                "error": r.get("error", "Unknown"),
            })

    push_logger.info(
        f"NOTIFICATION | Diffusion terminée | "
        f"envoyé={results['sent']} échoué={results['failed']} nettoyé={results['cleaned']}"
    )
    return results


def send_push_to_user(
    user_id: int,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/static/img/icons/icon-192x192.png",
    badge: str = "/static/img/icons/icon-72x72.png",
    tag: str = "transafrik",
    data: Optional[dict] = None,
    actions: Optional[list] = None,
    require_interaction: bool = False,
) -> dict:
    """Envoie une notification Push à tous les appareils d'un utilisateur."""
    subs = PushSubscription.query.filter_by(user_id=user_id).order_by(PushSubscription.id).all()
    results = {"success": True, "sent": 0, "failed": 0, "cleaned": 0}

    for sub in subs:
        r = _send_to_subscription(sub, title, body, url, icon, badge, tag, data, actions, require_interaction)
        if r.get("success"):
            results["sent"] += 1
        else:
            results["failed"] += 1
            if r.get("status_code") in (404, 410):
                remove_subscription_by_id(sub.id)
                results["cleaned"] += 1

    push_logger.info(
        f"NOTIFICATION | Envoi user_id={user_id} | "
        f"envoyé={results['sent']} échoué={results['failed']} nettoyé={results['cleaned']}"
    )
    return results


def _send_to_subscription(
    sub: PushSubscription,
    title: str,
    body: str,
    url: str = "/",
    icon: str = "/static/img/icons/icon-192x192.png",
    badge: str = "/static/img/icons/icon-72x72.png",
    tag: str = "transafrik",
    data: Optional[dict] = None,
    actions: Optional[list] = None,
    require_interaction: bool = False,
    ttl: int = 2419200,
) -> dict:
    """Envoi réel via pywebpush à un objet PushSubscription."""
    subscription_info = {
        "endpoint": sub.endpoint,
        "keys": {
            "p256dh": sub.p256dh,
            "auth": sub.auth,
        },
    }

    payload_data = data or {}
    payload_data.setdefault("url", url)
    payload_data.setdefault("date", datetime.utcnow().isoformat())

    notification_payload = {
        "title": title,
        "body": body,
        "icon": icon,
        "badge": badge,
        "tag": tag,
        "data": payload_data,
        "actions": actions or [],
        "requireInteraction": require_interaction,
        "vibrate": [200, 100, 200],
    }

    try:
        private_key = _get_vapid_private_key()
        public_key = _get_vapid_public_key()

        if not private_key or not public_key:
            push_logger.error("VAPID keys not configured — cannot send push")
            return {"success": False, "error": "Clés VAPID non configurées.", "status_code": 500}

        webpush(
            subscription_info=subscription_info,
            data=json.dumps(notification_payload),
            vapid_private_key=private_key,
            vapid_claims=_get_vapid_claims(),
            content_encoding="aes128gcm",
            ttl=ttl,
        )

        # Mettre à jour last_seen
        sub.last_seen = datetime.utcnow()
        db.session.commit()

        push_logger.info(
            f"ENVOYÉE | sub_id={sub.id} user={sub.user_id} "
            f"platform={sub.platform} browser={sub.browser} | \"{title}\""
        )
        return {"success": True, "message": "Notification envoyée."}

    except WebPushException as e:
        status_code = None
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            try:
                body_text = e.response.text[:200]
                error_msg = f"HTTP {status_code}: {body_text}"
            except Exception:
                error_msg = f"HTTP {status_code}"

        push_logger.warning(
            f"ERREUR {status_code} | sub_id={sub.id} user={sub.user_id} "
            f"platform={sub.platform} | {error_msg}"
        )

        return {"success": False, "error": error_msg, "status_code": status_code}

    except Exception as e:
        push_logger.error(
            f"EXCEPTION | sub_id={sub.id} user={sub.user_id} | {str(e)[:200]}"
        )
        return {"success": False, "error": str(e)[:500], "status_code": None}


# ───────────────────────────────────────────────
#  Génération clés VAPID
# ───────────────────────────────────────────────

def generate_vapid_keys() -> dict:
    """Génère une paire de clés VAPID (utilisé une seule fois pour la config)."""
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from base64 import urlsafe_b64encode

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_b64 = urlsafe_b64encode(private_bytes).rstrip(b'=').decode('ascii')
    public_b64 = urlsafe_b64encode(public_bytes).rstrip(b'=').decode('ascii')

    push_logger.info("VAPID | Nouvelles clés générées")

    return {
        "VAPID_PRIVATE_KEY": private_b64,
        "VAPID_PUBLIC_KEY": public_b64,
    }


def get_public_key_for_frontend() -> str:
    """Retourne la clé publique VAPID encodée (sans padding) pour le frontend JS."""
    pk = _get_vapid_public_key()
    if not pk:
        push_logger.warning("VAPID_PUBLIC_KEY non configurée")
        return ""
    # pywebpush attend une clé en base64 urlsafe sans padding
    return pk