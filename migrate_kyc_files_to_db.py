"""Migre le stockage KYC vers la base de données.

1. Ajoute les colonnes de contenu binaire et de mimetype à kyc_requests :
   document_front_data, document_front_mimetype,
   document_back_data, document_back_mimetype,
   selfie_data, selfie_mimetype.
2. (Best effort) Lit les fichiers déjà présents dans uploads/kyc/ et les
   enregistre en base pour les déploiements où ils existent encore.

Usage :
    python migrate_kyc_files_to_db.py
"""
import mimetypes
import os

from sqlalchemy import text

from app import app, db
from models import KycRequest

COLUMNS = [
    ("document_front_data", "BYTEA"),
    ("document_front_mimetype", "VARCHAR(100)"),
    ("document_back_data", "BYTEA"),
    ("document_back_mimetype", "VARCHAR(100)"),
    ("selfie_data", "BYTEA"),
    ("selfie_mimetype", "VARCHAR(100)"),
]


with app.app_context():
    # 1) Ajout des colonnes (idempotent)
    for col, typ in COLUMNS:
        try:
            db.session.execute(text(f"ALTER TABLE kyc_requests ADD COLUMN IF NOT EXISTS {col} {typ}"))
            db.session.commit()
            print(f"+ kyc_requests.{col} OK")
        except Exception as e:
            db.session.rollback()
            print(f"  kyc_requests.{col} skip: {e}")

    # 2) Migration des fichiers existants vers la base (si présents sur disque)
    kyc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'kyc')
    migrated = 0
    for kyc in KycRequest.query.all():
        for field in ('document_front', 'document_back', 'selfie'):
            filename = getattr(kyc, field, None)
            data = getattr(kyc, f'{field}_data', None)
            if not filename or data:
                continue
            path = os.path.join(kyc_dir, filename)
            if not os.path.exists(path):
                continue
            try:
                with open(path, 'rb') as f:
                    blob = f.read()
                setattr(kyc, f'{field}_data', blob)
                setattr(kyc, f'{field}_mimetype',
                        mimetypes.guess_type(filename)[0] or 'application/octet-stream')
                migrated += 1
            except Exception as e:
                print(f"  ! échec lecture {filename}: {e}")

    db.session.commit()
    print(f"Migration terminée — {migrated} fichier(s) migré(s) en base.")
