import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.models import User
from werkzeug.security import check_password_hash

app = create_app()
with app.app_context():
    users = User.query.all()
    if not users:
        print('No users found')
    for u in users:
        has_hash = bool(u.password_hash)
        matches_password = check_password_hash(u.password_hash, 'password') if has_hash else False
        print(u.id, u.email, u.name, u.role, 'has_hash=' + str(has_hash), 'password_ok=' + str(matches_password))
