"""Migration : ajoute la colonne qr_identifier à la table users."""
from app import app, db
from models import User

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text(
            'ALTER TABLE users ADD COLUMN IF NOT EXISTS qr_identifier VARCHAR(20) UNIQUE'
        ))
        conn.commit()
        print('OK - Colonne qr_identifier ajoutée.')