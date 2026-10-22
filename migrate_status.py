"""Crée les tables de la page de statut et insère les services par défaut.

Usage :
    python migrate_status.py
"""
from app import app, db
from models import ServiceStatus, StatusIncident

DEFAULT_SERVICES = [
    ("Application Web", "Systèmes", "Interface utilisateur TransAfrik", 1),
    ("API", "Systèmes", "API backend et endpoints", 2),
    ("Paiements Mobile Money", "Paiements", "Passerelle de paiement SoleasPay", 3),
    ("Dépôts", "Paiements", "Alimentation du portefeuille", 4),
    ("Retraits", "Paiements", "Transferts sortants", 5),
    ("Base de données", "Infrastructure", "Stockage des données", 6),
    ("Notifications (Email & Push)", "Infrastructure", "Emails et notifications push", 7),
]


with app.app_context():
    db.create_all()
    print("+ Tables service_statuses / status_incidents créées (si absentes).")

    if ServiceStatus.query.count() == 0:
        for name, category, desc, order in DEFAULT_SERVICES:
            db.session.add(ServiceStatus(
                name=name, category=category, description=desc,
                status='operational', sort_order=order,
            ))
        db.session.commit()
        print(f"+ {len(DEFAULT_SERVICES)} services par défaut insérés.")
    else:
        print("  Services déjà présents — aucun seed nécessaire.")
