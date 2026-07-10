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

    # Create Transaction & Beneficiary tables if not exist
    db.create_all()
    print("Migration complete.")