from app import create_app
from app.models import Ticket

app = create_app()
with app.app_context():
    cols = [c.name for c in Ticket.__table__.columns]
    print('columns:', cols)
    try:
        t = Ticket.query.first()
        print('first ticket:', t)
    except Exception as e:
        print('query error:', e)
        import traceback
        traceback.print_exc()
