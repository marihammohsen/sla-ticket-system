import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app

app = create_app()

with app.test_client() as client:
    for email in ['alice@example.com','bob@example.com','mimo@mimo.com']:
        resp = client.post('/auth/login', data={'email': email, 'password':'password'}, follow_redirects=True)
        ok = b'Welcome' in resp.data
        print(email, 'status', resp.status_code, 'welcome_in_page=', ok)
