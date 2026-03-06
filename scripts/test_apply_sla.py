from datetime import datetime
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.sla import apply_sla_on_create
from app.models import Ticket, SLAPolicy
from app import create_app

app = create_app()
with app.app_context():
    # make fake policy objects
    p1 = SLAPolicy(priority='P1', response_target_minutes=60, resolution_target_minutes=240)
    p2 = SLAPolicy(priority='P2', response_target_minutes=240, resolution_target_minutes=1440)
    for pri, policy in [('P1', p1), ('P2', p2)]:
        ticket = Ticket(priority=pri, sla_policy=policy)
        ticket.created_at = datetime(2025, 3, 14, 16, 30)
        apply_sla_on_create(ticket)
        print(pri, 'resp', ticket.response_due_at, 'resl', ticket.resolution_due_at)
