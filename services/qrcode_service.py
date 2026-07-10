"""
Service de QR Code TransAfrik.

Fonctionnalités :
- Génération de QR personnel (identifiant public TA-XXXX)
- Décodage de contenu JSON depuis un QR
- Validation de QR TransAfrik (type, champs obligatoires)
- Préparation pour extensions futures (marchand, dépôt, retrait, facture)

Bibliothèque : qrcode (PIL) — génération Python
Scanner : jsQR en JavaScript (voir static/js/scan.js)
"""

import json
import io
import base64
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

import qrcode
import qrcode.image.svg
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import RadialGradiantColorMask


# ═══════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════

QR_VERSION = "1.0"
QR_TYPE_USER = "transafrik_user"
QR_TYPE_MERCHANT = "transafrik_merchant"    # futur
QR_TYPE_DEPOSIT = "transafrik_deposit"      # futur
QR_TYPE_WITHDRAW = "transafrik_withdraw"    # futur
QR_TYPE_INVOICE = "transafrik_invoice"      # futur

VALID_QR_TYPES = {
    QR_TYPE_USER,
    QR_TYPE_MERCHANT,
    QR_TYPE_DEPOSIT,
    QR_TYPE_WITHDRAW,
    QR_TYPE_INVOICE,
}

# Champs obligatoires par type de QR
REQUIRED_FIELDS: Dict[str, set] = {
    QR_TYPE_USER: {"type", "user_id", "name", "phone", "country", "operator", "qr_id"},
    QR_TYPE_MERCHANT: {"type", "merchant_id", "name", "phone", "country"},
    QR_TYPE_DEPOSIT: {"type", "user_id", "phone", "country", "operator"},
    QR_TYPE_WITHDRAW: {"type", "user_id", "amount", "currency"},
    QR_TYPE_INVOICE: {"type", "invoice_id", "amount", "currency", "merchant_name"},
}


# ═══════════════════════════════════════════════════════════
# GÉNÉRATION D'IDENTIFIANT PUBLIC
# ═══════════════════════════════════════════════════════════

def generate_qr_identifier() -> str:
    """Génère un identifiant public unique pour le QR Code.

    Format : TA-XXXXXXXXXX (10 caractères alphanumériques)
    Exemple : TA-7G82KQ91M

    L'identifiant est dérivé d'un UUID4 + timestamp pour garantir l'unicité,
    puis tronqué à 10 caractères.
    """
    raw = uuid.uuid4().hex + str(int(datetime.utcnow().timestamp()))
    hashed = hashlib.sha256(raw.encode()).hexdigest().upper()
    # Prendre 10 caractères en sautant les premiers pour plus d'entropie
    short = hashed[8:18]
    return f"TA-{short}"


# ═══════════════════════════════════════════════════════════
# GÉNÉRATION DE QR CODE
# ═══════════════════════════════════════════════════════════

def generate_user_qrcode(user) -> Tuple[str, str]:
    """Génère le QR Code personnel d'un utilisateur.

    Args:
        user: Instance du modèle User.

    Returns:
        Tuple (qr_data_json, qr_image_base64_png)
        - qr_data_json : le contenu texte du QR en JSON string
        - qr_image_base64_png : l'image PNG encodée en base64 (data URI)
    """
    # Construire le payload JSON
    payload = {
        "type": QR_TYPE_USER,
        "version": QR_VERSION,
        "qr_id": user.qr_identifier,
        "user_id": user.id,
        "name": user.fullname,
        "phone": user.phone,
        "country": user.country,
        "operator": _get_user_operator(user),
    }

    qr_data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    # Générer l'image QR avec style
    qr = qrcode.QRCode(
        version=None,  # auto
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% redondance
        box_size=12,
        border=2,
    )
    qr.add_data(qr_data_json)
    qr.make(fit=True)

    # Créer l'image
    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=RadialGradiantColorMask(
            back_color=(255, 255, 255),
            center_color=(37, 99, 235),       # blue-600
            edge_color=(5, 150, 105),          # emerald-600
        ),
    )

    # Convertir en base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    img_data_uri = f"data:image/png;base64,{b64}"

    return qr_data_json, img_data_uri


def generate_qrcode_svg(user) -> str:
    """Génère le QR Code au format SVG (vectoriel) pour l'impression.

    Args:
        user: Instance du modèle User.

    Returns:
        Chaîne SVG complète.
    """
    payload = {
        "type": QR_TYPE_USER,
        "version": QR_VERSION,
        "qr_id": user.qr_identifier,
        "user_id": user.id,
        "name": user.fullname,
        "phone": user.phone,
        "country": user.country,
        "operator": _get_user_operator(user),
    }
    qr_data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr.add_data(qr_data_json)
    qr.make(fit=True)

    factory = qrcode.image.svg.SvgImage
    img = qr.make_image(image_factory=factory)
    return img.to_string(encoding="unicode")


# ═══════════════════════════════════════════════════════════
# DÉCODAGE
# ═══════════════════════════════════════════════════════════

def decode_qrcode(data: str) -> Optional[Dict[str, Any]]:
    """Décode le contenu texte d'un QR Code en dictionnaire Python.

    Args:
        data: Chaîne brute lue depuis le QR Code (supposée JSON).

    Returns:
        Dictionnaire décodé, ou None si données invalides.
    """
    if not data or not isinstance(data, str):
        return None

    data = data.strip()

    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, ValueError):
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


# ═══════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════

def is_transafrik_qrcode(data: str) -> bool:
    """Vérifie si une chaîne est un QR Code TransAfrik valide.

    Vérifications :
    1. JSON parsable
    2. Champ 'type' présent et reconnu
    3. Tous les champs obligatoires présents

    Args:
        data: Chaîne brute du QR Code.

    Returns:
        True si le QR est un QR TransAfrik valide, False sinon.
    """
    parsed = decode_qrcode(data)
    if parsed is None:
        return False

    qr_type = parsed.get("type", "")
    if qr_type not in VALID_QR_TYPES:
        return False

    required = REQUIRED_FIELDS.get(qr_type, set())
    for field in required:
        if field not in parsed or parsed[field] is None:
            return False

    return True


def validate_qrcode(data: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Valide un QR Code et retourne un résultat détaillé.

    Args:
        data: Chaîne brute du QR Code.

    Returns:
        Tuple (is_valid, parsed_dict_or_None, error_message_or_None)
    """
    parsed = decode_qrcode(data)
    if parsed is None:
        return False, None, "Données invalides : JSON illisible."

    qr_type = parsed.get("type", "")
    if qr_type not in VALID_QR_TYPES:
        return False, parsed, f"Type de QR inconnu : {qr_type}"

    required = REQUIRED_FIELDS.get(qr_type, set())
    missing = [f for f in required if f not in parsed or parsed[f] is None]
    if missing:
        return False, parsed, f"Champs manquants : {', '.join(missing)}"

    return True, parsed, None


def get_qr_action(qr_type: str) -> str:
    """Retourne l'URL d'action pour un type de QR donné.

    Args:
        qr_type: Le type de QR (ex: 'transafrik_user').

    Returns:
        URL relative vers la page d'action.
    """
    actions = {
        QR_TYPE_USER: "/send-money",
        QR_TYPE_MERCHANT: "/send-money",     # futur : /pay
        QR_TYPE_DEPOSIT: "/deposit",
        QR_TYPE_WITHDRAW: "/withdraw",       # futur
        QR_TYPE_INVOICE: "/send-money",      # futur : /invoice/pay
    }
    return actions.get(qr_type, "/send-money")


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _get_user_operator(user) -> str:
    """Déduit l'opérateur principal de l'utilisateur depuis son pays.

    Pour l'instant, retourne le premier opérateur du pays.
    Dans le futur, l'utilisateur pourra configurer son opérateur par défaut.
    """
    from config.operators import get_active_operators_for_country
    ops = get_active_operators_for_country(user.country)
    if ops and len(ops) > 0:
        return ops[0].get("name", "Inconnu").upper()
    return "Inconnu"


def get_scan_history_from_db(user_id, limit=20):
    """Récupère l'historique des scans depuis la base de données.

    Pour l'instant, utilise les bénéficiaires récents comme proxy.
    Dans le futur, une table ScanHistory dédiée sera créée.

    Args:
        user_id: ID de l'utilisateur connecté.
        limit: Nombre maximum d'entrées.

    Returns:
        Liste de dictionnaires.
    """
    from models import Beneficiary
    beneficiaries = Beneficiary.query.filter_by(user_id=user_id) \
        .order_by(Beneficiary.created_at.desc()).limit(limit).all()

    history = []
    for b in beneficiaries:
        history.append({
            "name": b.name or "Inconnu",
            "phone": b.phone or "",
            "country": b.country or "",
            "operator": b.operator or "",
            "date": b.created_at.strftime("%d/%m/%Y") if b.created_at else "",
            "time": b.created_at.strftime("%H:%M") if b.created_at else "",
        })
    return history