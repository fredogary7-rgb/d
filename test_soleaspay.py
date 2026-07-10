#!/usr/bin/env python
"""
Script de test pour le client SoleasPay.

Teste les deux opérations principales :
  1. pay_in()   — Collecter un paiement (Pay-In)
  2. withdraw() — Distribuer un paiement (Payout)

Utilisation :
    python test_soleaspay.py

Prérequis :
    - Un fichier .env avec SOLEAS_API_KEY et SOLEAS_BEARER_TOKEN
    - Le package `requests` installé
    - Le package `python-dotenv` installé (pour charger .env)

Ce script est autonome et ne touche à aucune route Flask ni base de données.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from services.soleaspay import pay_in, withdraw, SOLEAS_WALLET
from config.operators import get_service_id, OPERATORS


def check_env():
    required = {
        "SOLEAS_API_KEY": os.getenv("SOLEAS_API_KEY"),
        "SOLEAS_BEARER_TOKEN": os.getenv("SOLEAS_BEARER_TOKEN"),
        "SOLEAS_WALLET": os.getenv("SOLEAS_WALLET"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print("\n" + "=" * 60)
        print("⚠️  Variables d'environnement manquantes :")
        for m in missing:
            print(f"   - {m}")
        print("=" * 60 + "\n")
        return False
    print("\n✅ Variables d'environnement OK")
    return True


def print_result(name, result):
    success = result.get("success", False)
    icon = "✅" if success else "❌"
    print(f"   Résultat {name} : {icon}")
    if success:
        code = result.get("code", "?")
        status = result.get("status", "?")
        ref = result.get("data", {}).get("reference", "N/A") if isinstance(result.get("data"), dict) else "N/A"
        print(f"   Code: {code}  Statut: {status}  Réf: {ref}")
    else:
        print(f"   Erreur: {result.get('message', 'Inconnue')}")


def test_pay_in():
    print("\n" + "=" * 60)
    print("🧪 TEST 1 : pay_in()")
    print("=" * 60)
    order_id = f"TEST-ORDER-{os.urandom(4).hex()}"
    result = pay_in(
        service=29, wallet="0707070707", amount=100, currency="XOF",
        order_id=order_id, description="Test Pay-In",
        payer="Jean Testeur", payer_email="jean@example.com",
        success_url="https://transafrik.com/test/success",
        failure_url="https://transafrik.com/test/failure",
    )
    print_result("pay_in", result)
    return result


def test_withdraw():
    print("\n" + "=" * 60)
    print("🧪 TEST 2 : withdraw()")
    print("=" * 60)
    result = withdraw(service=29, wallet="0101010101", amount=50, currency="XOF")
    print_result("withdraw", result)
    return result


def test_operator_resolution():
    print("\n" + "=" * 60)
    print("🧪 TEST 3 : Résolution des IDs")
    print("=" * 60)
    test_cases = [
        ("TG", "tmoney", 37), ("TG", "moov", 38),
        ("CI", "orange", 29), ("CI", "mtn", 30), ("CI", "moov", 31), ("CI", "wave", 32),
        ("BF", "moov", 33), ("BF", "orange", 34),
        ("BJ", "mtn", 35), ("BJ", "moov", 36),
        ("CD", "vodacom", 52), ("CD", "airtel", 53), ("CD", "orange", 54),
        ("CG", "airtel", 55), ("CG", "mtn", 56),
        ("GA", "airtel", 57),
        ("UG", "airtel", 58), ("UG", "mtn", 59),
        ("CM", "mtn", 1), ("CM", "orange", 2),
        ("ZM", "airtel", 60), ("ZM", "mtn", 61), ("ZM", "zamtel", 62),
        ("SN", "orange", 24), ("SN", "wave", 25), ("SN", "free", 26),
        ("SN", "expresso", 27), ("SN", "wizall", 28),
    ]
    all_ok = True
    for country, slug, expected in test_cases:
        result_id = get_service_id(country, slug)
        ok = result_id == expected
        if not ok:
            all_ok = False
        print(f"   {'✅' if ok else '❌'} {country}/{slug} -> {result_id} (attendu: {expected})")
    print(f"\n   {'✅ Tous corrects' if all_ok else '❌ Erreurs détectées'}")
    return all_ok


def test_operator_count():
    print("\n" + "=" * 60)
    print("🧪 TEST 4 : Résumé")
    print("=" * 60)
    active = sum(1 for o in OPERATORS.values() if o["active"])
    inactive = sum(1 for o in OPERATORS.values() if not o["active"])
    mm = sum(1 for o in OPERATORS.values() if o["type"] == "mobile_money")
    print(f"   Total: {len(OPERATORS)}  |  Actifs: {active}  |  Inactifs: {inactive}  |  Mobile Money: {mm}")


def main():
    print("=" * 60)
    print("  🧪 SUITE DE TESTS — Client SoleasPay")
    print("=" * 60)
    env_ok = check_env()
    test_operator_resolution()
    test_operator_count()
    if env_ok:
        print("\n🚀 Exécution des tests API...")
        test_pay_in()
        test_withdraw()
    else:
        print("\n⚠️  Tests API SKIPPÉS (variables manquantes)")
    print("\n" + "=" * 60)
    print("  ✅ Terminé.")
    print("=" * 60)


if __name__ == "__main__":
    main()