"""Add missing columns to users table (PostgreSQL-compatible)."""
from app import app, db
from sqlalchemy import text

with app.app_context():
    migrations = [
        ("balance", "INTEGER DEFAULT 0"),
        ("pending_balance", "INTEGER DEFAULT 0"),
        ("currency", "VARCHAR(10) DEFAULT 'XOF'"),
        ("profile_picture", "VARCHAR(255)"),
        ("kyc_status", "VARCHAR(20) DEFAULT 'pending'"),
        ("referral_code", "VARCHAR(30)"),
    ]
    for col, typ in migrations:
        try:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"))
            db.session.commit()
            print(f"+ users.{col} OK")
        except Exception as e:
            db.session.rollback()
            print(f"  users.{col} skip: {e}")

    # --- Nouveaux champs pour beneficiaries ---
    beneficiary_cols = [
        ("email", "VARCHAR(255)"),
        ("nickname", "VARCHAR(100)"),
        ("photo", "VARCHAR(500)"),
        ("is_favorite", "BOOLEAN DEFAULT FALSE"),
        ("transfer_count", "INTEGER DEFAULT 0"),
        ("total_sent", "INTEGER DEFAULT 0"),
        ("last_transfer_at", "TIMESTAMP"),
        ("updated_at", "TIMESTAMP DEFAULT NOW()"),
    ]
    for col, typ in beneficiary_cols:
        try:
            db.session.execute(text(f"ALTER TABLE beneficiaries ADD COLUMN IF NOT EXISTS {col} {typ}"))
            db.session.commit()
            print(f"+ beneficiaries.{col} OK")
        except Exception as e:
            db.session.rollback()
            print(f"  beneficiaries.{col} skip: {e}")

    # --- Nouveaux champs settings (last_login, language, pin_hash, is_deleted) ---
    settings_cols = [
        ("last_login", "TIMESTAMP"),
        ("language", "VARCHAR(10) DEFAULT 'fr'"),
        ("pin_hash", "VARCHAR(255)"),
        ("is_deleted", "BOOLEAN DEFAULT FALSE"),
    ]
    for col, typ in settings_cols:
        try:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typ}"))
            db.session.commit()
            print(f"+ users.{col} OK")
        except Exception as e:
            db.session.rollback()
            print(f"  users.{col} skip: {e}")

    # --- Table KYC Requests ---
    try:
        db.create_all()  # Crée la table kyc_requests si elle n'existe pas
        print("+ kyc_requests table OK (via create_all)")
    except Exception as e:
        print(f"  kyc_requests skip: {e}")

    # --- Créer dossier uploads/kyc s'il n'existe pas ---
    import os
    kyc_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads', 'kyc')
    os.makedirs(kyc_dir, exist_ok=True)
    print(f"+ uploads/kyc directory OK")

    # Create Transaction & Beneficiary tables if not exist
    print("Migration complete.")
