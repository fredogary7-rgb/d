"""
Mapping centralisé des IDs de service SoleasPay.
Alias léger — la source unique de vérité est config/operators.py.

Ce module réexporte get_service_id depuis config/operators.py pour
la rétro-compatibilité.

Ne jamais écrire service=37 directement dans le code.
Toujours utiliser get_service_id(country_code, operator_slug).
"""

from config.operators import get_service_id  # noqa: F401


# Alias rétro-compatible pour le code existant
SERVICE_IDS = {
    # CAMEROUN
    "CM": {"mtn": 1, "orange": 2},
    # CÔTE D'IVOIRE
    "CI": {"orange": 29, "mtn": 30, "moov": 31, "wave": 32},
    # BURKINA FASO
    "BF": {"moov": 33, "orange": 34},
    # BÉNIN
    "BJ": {"mtn": 35, "moov": 36},
    # TOGO
    "TG": {"tmoney": 37, "moov": 38},
    # RD CONGO
    "CD": {"vodacom": 52, "airtel": 53, "orange": 54},
    # CONGO BRAZZAVILLE
    "CG": {"airtel": 55, "mtn": 56},
    # GABON
    "GA": {"airtel": 57},
    # OUGANDA
    "UG": {"airtel": 58, "mtn": 59},
    # ZAMBIE
    "ZM": {"airtel": 60, "mtn": 61, "zamtel": 62},
    # SÉNÉGAL
    "SN": {"orange": 24, "wave": 25, "free": 26, "expresso": 27, "wizall": 28},
}