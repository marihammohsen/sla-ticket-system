from datetime import datetime, timedelta
import random

from werkzeug.security import generate_password_hash

from app import create_app, db


app = create_app()


@app.cli.command("init-db")
def init_db_command():
    """Initialize the database and seed basic data."""
    from app.models import User, SLAPolicy

    db.drop_all()
    db.create_all()

    # Seed SLA policies
    policies = [
        SLAPolicy(priority="P1", response_target_minutes=60, resolution_target_minutes=240),
        SLAPolicy(priority="P2", response_target_minutes=240, resolution_target_minutes=1440),
        SLAPolicy(priority="P3", response_target_minutes=480, resolution_target_minutes=1440),
        SLAPolicy(priority="P4", response_target_minutes=1440, resolution_target_minutes=4320),
    ]
    db.session.add_all(policies)

    # Seed simple users with passwords "password"
    users = [
        User(
            name="Alice Agent",
            email="alice@example.com",
            role="agent",
            password_hash=generate_password_hash("password"),
        ),
        User(
            name="Bob Manager",
            email="bob@example.com",
            role="manager",
            password_hash=generate_password_hash("password"),
        ),
    ]
    db.session.add_all(users)

    db.session.commit()
    print("Database initialized with SLA policies and sample users.")


@app.cli.command("seed-demo-data")
def seed_demo_data_command():
    """Create a set of demo tickets for dashboards and testing."""
    from app.models import Ticket, User, SLAPolicy
    from app.services.tickets import calculate_priority
    from app.services.sla import apply_sla_on_create

    agents = User.query.filter_by(role="agent").all()
    if not agents:
        print("No agents found, run init-db first.")
        return

    policies = {p.priority: p for p in SLAPolicy.query.all()}
    if not policies:
        print("No SLA policies found, run init-db first.")
        return

    titles = [
        "Email service outage",
        "VPN connection unstable",
        "New laptop request",
        "Password reset issue",
        "Slow ERP performance",
        "Shared drive access request",
    ]

    now = datetime.utcnow()
    created_tickets = []

    for i, title in enumerate(titles, start=1):
        if "request" in title.lower():
            issue_type = "service_request"
            impact = None
            urgency = None
        else:
            issue_type = random.choice(["incident", "problem"])
            impact = random.choice(["high", "medium", "low"])
            urgency = random.choice(["high", "medium", "low"])

        priority = calculate_priority(issue_type, impact, urgency)
        sla_policy = policies.get(priority)
        agent = random.choice(agents)

        created_at = now - timedelta(hours=random.randint(1, 72))

        ticket = Ticket(
            title=title,
            description=f"Auto-generated demo ticket: {title}.",
            issue_type=issue_type,
            impact=impact,
            urgency=urgency,
            system_affected="Core system" if issue_type != "service_request" else None,
            request_category="Hardware" if "laptop" in title.lower() else "Access",
            department="IT",
            approval_required=True if "request" in title.lower() else False,
            priority=priority,
            sla_policy=sla_policy,
            status="new",
            assignee=agent,
            created_by=agent,
            created_at=created_at,
        )

        apply_sla_on_create(ticket)
        created_tickets.append(ticket)
        db.session.add(ticket)

    db.session.commit()
    print(f"Created {len(created_tickets)} demo tickets.")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Flask app running at: http://192.168.1.104:5000")
    print("Share this URL with your colleague")
    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)

