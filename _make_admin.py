"""Script : definir ameket4@gmail.com comme super_admin"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import app, db
from models import User
from admin.models import AdminUser

with app.app_context():
    # Créer les tables admin si elles n'existent pas
    db.create_all()

    email = 'ameket4@gmail.com'
    user = User.query.filter_by(email=email).first()

    if not user:
        print(f'ERREUR : Aucun utilisateur trouvé avec l\'email {email}')
        sys.exit(1)

    print(f'Utilisateur trouvé : {user.fullname} (ID: {user.id}, Email: {user.email})')

    # Vérifier s'il est déjà admin
    existing_admin = AdminUser.query.filter_by(user_id=user.id).first()
    if existing_admin:
        print(f'Déjà admin avec le rôle : {existing_admin.role}')
        if existing_admin.role != 'super_admin':
            existing_admin.role = 'super_admin'
            db.session.commit()
            print(f'Rôle mis à jour : super_admin')
    else:
        admin = AdminUser(
            user_id=user.id,
            role='super_admin',
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin créé avec succès ! Rôle : super_admin')

    # Vérification finale
    admin_check = AdminUser.query.filter_by(user_id=user.id).first()
    print(f'\nVérification : AdminUser.id={admin_check.id}, role={admin_check.role}, active={admin_check.is_active}')
    print('Terminé.')