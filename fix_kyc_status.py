"""Synchronise User.kyc_status avec KycRequest.status.

Corrige deux problèmes :
1. Les utilisateurs n'ayant jamais soumis de KYC étaient en "pending" (défaut).
   -> ils passent en "none".
2. Les dossiers approuvés/refusés par un admin ne mettaient à jour que
   User.kyc_status, pas KycRequest.status.
   -> on resynchronise KycRequest.status.

Usage :
    python fix_kyc_status.py
"""
from datetime import datetime

from app import app, db
from models import KycRequest, User


with app.app_context():
    # 1) Rétro-synchronise KycRequest.status pour les comptes déjà vérifiés/refusés
    for user in User.query.filter(User.kyc_status.in_(['verified', 'rejected'])).all():
        kyc = KycRequest.query.filter_by(user_id=user.id).first()
        if not kyc:
            continue
        target = 'APPROVED' if user.kyc_status == 'verified' else 'REJECTED'
        if kyc.status != target:
            kyc.status = target
            if target == 'APPROVED' and not kyc.verified_at:
                kyc.verified_at = datetime.utcnow()
    db.session.commit()

    # 2) Recalcule User.kyc_status d'après le dossier KYC réel
    changed = 0
    for user in User.query.filter_by(is_deleted=False).all():
        kyc = KycRequest.query.filter_by(user_id=user.id).first()
        if kyc and kyc.status in ('SUBMITTED', 'UNDER_REVIEW'):
            desired = 'pending'
        elif kyc and kyc.status == 'APPROVED':
            desired = 'verified'
        elif kyc and kyc.status == 'REJECTED':
            desired = 'rejected'
        else:
            desired = 'none'
        if user.kyc_status != desired:
            user.kyc_status = desired
            changed += 1
    db.session.commit()
    print(f"KYC statuses synchronisés — {changed} utilisateur(s) mis à jour.")

    print("Répartition :")
    for s in ('none', 'pending', 'verified', 'rejected'):
        c = User.query.filter_by(is_deleted=False, kyc_status=s).count()
        print(f"  {s}: {c}")
