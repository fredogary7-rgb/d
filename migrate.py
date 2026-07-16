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

    # --- Nouveaux champs profil ---
    profile_cols = [
        ("birth_date", "DATE"),
        ("gender", "VARCHAR(10)"),
        ("profession", "VARCHAR(150)"),
        ("address", "VARCHAR(300)"),
        ("city", "VARCHAR(100)"),
        ("postal_code", "VARCHAR(20)"),
        ("theme", "VARCHAR(10) DEFAULT 'light'"),
        ("two_factor_enabled", "BOOLEAN DEFAULT FALSE"),
        ("two_factor_method", "VARCHAR(20)"),
        ("last_ip", "VARCHAR(45)"),
        ("updated_at", "TIMESTAMP"),
        ("daily_limit", "INTEGER DEFAULT 500000"),
        ("monthly_limit", "INTEGER DEFAULT 5000000"),
        ("used_daily", "INTEGER DEFAULT 0"),
        ("used_monthly", "INTEGER DEFAULT 0"),
        ("notification_email", "BOOLEAN DEFAULT TRUE"),
        ("notification_sms", "BOOLEAN DEFAULT TRUE"),
        ("notification_push", "BOOLEAN DEFAULT TRUE"),
        ("vibrations", "BOOLEAN DEFAULT TRUE"),
        ("referred_by", "INTEGER"),
    ]
    for col, typ in profile_cols:
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

    # --- Colonne email pour otp_codes ---
    try:
        db.session.execute(text("ALTER TABLE otp_codes ADD COLUMN IF NOT EXISTS email VARCHAR(255)"))
        db.session.commit()
        print("+ otp_codes.email OK")
    except Exception as e:
        db.session.rollback()
        print(f"  otp_codes.email skip: {e}")

    # --- Table push_subscriptions (Web Push) ---
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                subscription_json JSONB NOT NULL,
                endpoint VARCHAR(1024) NOT NULL,
                platform VARCHAR(50),
                browser VARCHAR(50),
                device_name VARCHAR(255),
                user_agent TEXT,
                keys_p256dh TEXT,
                keys_auth TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                last_seen TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.session.commit()
        print("+ push_subscriptions table OK")

        # Indexes
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id ON push_subscriptions(user_id)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_endpoint ON push_subscriptions(endpoint)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_platform ON push_subscriptions(platform)
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_browser ON push_subscriptions(browser)
        """))
        db.session.commit()
        print("+ push_subscriptions indexes OK")
    except Exception as e:
        db.session.rollback()
        print(f"  push_subscriptions skip: {e}")

    # Create Transaction & Beneficiary tables if not exist
    print("Migration complete.")
