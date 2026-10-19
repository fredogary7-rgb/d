"""Corrige la colonne nationality (trop courte) et backfill du pays KYC.

- Élargit kyc_requests.nationality de VARCHAR(5) à VARCHAR(50).
- Remplit kyc_requests.country à partir de users.country quand il est vide.

Usage :
    python fix_kyc_nationality.py
"""
from sqlalchemy import text

from app import app, db


with app.app_context():
    try:
        db.session.execute(text(
            "ALTER TABLE kyc_requests ALTER COLUMN nationality TYPE VARCHAR(50)"
        ))
        db.session.commit()
        print("+ kyc_requests.nationality -> VARCHAR(50) OK")
    except Exception as e:
        db.session.rollback()
        print(f"  nationality skip: {e}")

    try:
        res = db.session.execute(text(
            "UPDATE kyc_requests k "
            "SET country = u.country "
            "FROM users u "
            "WHERE k.user_id = u.id AND (k.country IS NULL OR k.country = '')"
        ))
        db.session.commit()
        print(f"+ country backfill: {res.rowcount} dossier(s) mis à jour")
    except Exception as e:
        db.session.rollback()
        print(f"  country backfill skip: {e}")
