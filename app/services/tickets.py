from datetime import datetime, timezone
from typing import Optional

from ..models import SLAPolicy, Ticket
from . import sla


IMPACT_URGENCY_MATRIX = {
    ("high", "high"): "P1",
    ("high", "medium"): "P2",
    ("high", "low"): "P3",
    ("medium", "high"): "P2",
    ("medium", "medium"): "P3",
    ("medium", "low"): "P4",
    ("low", "high"): "P3",
    ("low", "medium"): "P4",
    ("low", "low"): "P4",
}


def calculate_priority(issue_type: str, impact: Optional[str], urgency: Optional[str]) -> str:
    """Return P1-P4 based on issue_type, impact and urgency.

    Service Requests default to P3.
    """
    issue_type = (issue_type or "").lower()
    impact = (impact or "").lower()
    urgency = (urgency or "").lower()

    if issue_type == "service_request":
        return "P3"

    return IMPACT_URGENCY_MATRIX.get((impact, urgency), "P4")


def get_sla_policy_for_priority(priority: str) -> Optional[SLAPolicy]:
    """Fetch the SLA policy row for a given priority."""
    return SLAPolicy.query.filter_by(priority=priority).first()


ALLOWED_STATUS_TRANSITIONS = {
    "new": {"in_progress", "on_hold", "resolved"},
    "in_progress": {"on_hold", "resolved"},
    "on_hold": {"in_progress", "resolved"},
    "resolved": {"in_progress", "closed"},
    "closed": set(),
}


def transition_status(ticket: Ticket, new_status: str, now: Optional[datetime] = None) -> None:
    """Apply a status transition with SLA-related side effects.

    This does not commit the database session; callers must commit.
    """
    now = now or datetime.now(timezone.utc)
    current = (ticket.status or "").lower()
    new_status = (new_status or "").lower()

    if new_status == current:
        return

    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid status transition from {current} to {new_status}")

    # Handle pause windows around On Hold
    sla.update_pause_on_status_change(ticket, new_status, now=now)

    # Set timestamps for first response and resolution
    if current == "new" and new_status in {"in_progress", "resolved"}:
        sla.record_first_response_if_needed(ticket, now=now)

    if new_status == "resolved":
        sla.record_resolved_if_needed(ticket, now=now)

    ticket.status = new_status

    # Update breach flags after the change
    sla.refresh_breach_flags(ticket, now=now)

