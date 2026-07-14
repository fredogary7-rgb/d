import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from app import app, db
from models import User

with app.app_context():
    users = User.query.filter_by(is_deleted=False).all()
    print(f"Nombre d'utilisateurs : {len(users)}")
    for u in users:
        print(f"  ID={u.id} | {u.email} | {u.fullname} | phone={u.phone}")