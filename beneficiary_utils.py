"""Utilitaires pour la gestion des bénéficiaires."""

from datetime import datetime


def format_phone_display(phone: str) -> str:
    """Formate un numéro de téléphone pour l'affichage."""
    if not phone:
        return ''
    clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    if len(clean) <= 4:
        return clean
    return f'•••• {clean[-4:]}'


def get_avatar_initials(name: str) -> str:
    """Retourne les initiales pour l'avatar (2 caractères max)."""
    if not name:
        return '?'
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return parts[0][:2].upper()


def get_operator_color(operator: str) -> str:
    """Retourne la classe CSS de couleur pour un opérateur."""
    mapping = {
        'TMONEY': '#FFB300',
        'MOOV': '#006699',
        'MTN': '#FFCC00',
        'ORANGE': '#FF6600',
        'WAVE': '#0055CC',
        'AIRTEL': '#EE0000',
        'VODACOM': '#E60000',
        'FREE': '#E91E63',
        'WIZALL': '#9C27B0',
        'ZAMTEL': '#4CAF50',
    }
    return mapping.get(operator.upper(), '#64748B')