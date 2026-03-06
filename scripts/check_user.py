import os
import sys

# Ensure project root is on sys.path when running from arbitrary cwd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.models import User

app = create_app()
with app.app_context():
    email = 'mimo@mimo.com'
    u = User.query.filter_by(email=email).first()
    if u:
        print('FOUND', u.id, u.email, u.name, u.role)
    else:
        print('NOT FOUND')
