"""Migration : ajoute les colonnes reference et status_message à la table transactions."""
from app import app, db

with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text(
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS reference VARCHAR(64)'
        ))
        conn.execute(db.text(
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS status_message TEXT'
        ))
        conn.commit()
        print('OK - Colonnes reference et status_message ajoutées à transactions.')
