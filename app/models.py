from datetime import datetime

from . import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'agent' or 'manager'
    password_hash = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class SLAPolicy(db.Model):
    __tablename__ = "sla_policies"

    id = db.Column(db.Integer, primary_key=True)
    priority = db.Column(db.String(5), unique=True, nullable=False)  # P1-P4
    response_target_minutes = db.Column(db.Integer, nullable=False)
    resolution_target_minutes = db.Column(db.Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<SLAPolicy {self.priority}>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)

    issue_type = db.Column(db.String(50), nullable=False)  # incident, problem, service_request
    impact = db.Column(db.String(20))  # high, medium, low (for incident/problem)
    urgency = db.Column(db.String(20))  # high, medium, low (for incident/problem)
    system_affected = db.Column(db.String(200))

    request_category = db.Column(db.String(100))
    department = db.Column(db.String(100))
    approval_required = db.Column(db.Boolean)

    priority = db.Column(db.String(5), nullable=False)  # P1-P4
    sla_policy_id = db.Column(db.Integer, db.ForeignKey("sla_policies.id"), nullable=False)
    sla_policy = db.relationship("SLAPolicy")

    # Lifecycle / SLA tracking
    status = db.Column(db.String(20), default="new", nullable=False)

    response_due_at = db.Column(db.DateTime)
    resolution_due_at = db.Column(db.DateTime)

    first_response_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)

    on_hold_started_at = db.Column(db.DateTime)
    total_pause_duration_seconds = db.Column(db.Integer, default=0, nullable=False)

    response_breached = db.Column(db.Boolean, default=False, nullable=False)
    resolution_breached = db.Column(db.Boolean, default=False, nullable=False)
    escalation_level = db.Column(db.Integer, default=0)
    is_escalated = db.Column(db.Boolean, default=False)
    escalation_note = db.Column(db.Text, nullable=True)


    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    assignee = db.relationship("User", foreign_keys=[assignee_id])

    # track which manager (or user) performed the assignment
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Ticket {self.id} - {self.title}>"


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    ticket = db.relationship("Ticket", backref=db.backref("comments", order_by="TicketComment.created_at"))
    author = db.relationship("User")

    def __repr__(self) -> str:
        return f"<TicketComment {self.id} on Ticket {self.ticket_id}>"

