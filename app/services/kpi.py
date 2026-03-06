from datetime import datetime

from sqlalchemy import func

from .. import db
from ..models import Ticket


def _base_query():
    return db.session.query(Ticket)


def get_sla_compliance_rate() -> float:
    """Return overall SLA compliance rate based on resolution breaches."""
    q = _base_query()
    total = q.count()
    if total == 0:
        return 100.0

    within_sla = q.filter(Ticket.resolution_breached.is_(False)).count()
    return round((within_sla / total) * 100.0, 1)


def get_breached_counts() -> dict:
    q = _base_query()
    response_breached = q.filter(Ticket.response_breached.is_(True)).count()
    resolution_breached = q.filter(Ticket.resolution_breached.is_(True)).count()
    return {
        "response_breached": response_breached,
        "resolution_breached": resolution_breached,
    }


def get_avg_response_time_minutes() -> float:
    """Average time to first response in minutes (excluding tickets with no response)."""
    q = (
        db.session.query(
            func.avg(
                func.julianday(Ticket.first_response_at) - func.julianday(Ticket.created_at)
                - (Ticket.total_pause_duration_seconds / 86400.0)
            )
        )
        .filter(Ticket.first_response_at.is_not(None))
    )
    days = q.scalar()
    if days is None:
        return 0.0
    return round(days * 24 * 60, 1)


def get_avg_resolution_time_minutes() -> float:
    """Average time to resolution in minutes (excluding tickets not resolved)."""
    q = (
        db.session.query(
            func.avg(
                func.julianday(Ticket.resolved_at) - func.julianday(Ticket.created_at)
                - (Ticket.total_pause_duration_seconds / 86400.0)
            )
        )
        .filter(Ticket.resolved_at.is_not(None))
    )
    days = q.scalar()
    if days is None:
        return 0.0
    return round(days * 24 * 60, 1)


def get_ticket_counts_by_priority() -> dict:
    rows = (
        db.session.query(Ticket.priority, func.count(Ticket.id))
        .group_by(Ticket.priority)
        .all()
    )
    return {priority: count for priority, count in rows}


def get_ticket_counts_by_type() -> dict:
    rows = (
        db.session.query(Ticket.issue_type, func.count(Ticket.id))
        .group_by(Ticket.issue_type)
        .all()
    )
    return {issue_type: count for issue_type, count in rows}

