from datetime import datetime, timedelta, timezone
from typing import Optional

from ..models import Ticket


def _now() -> datetime:
    return datetime.now(timezone.utc)


# business day boundaries (UTC assumed)
_BUSINESS_START_HOUR = 9
_BUSINESS_END_HOUR = 17


def _is_business_time(dt: datetime) -> bool:
    # Monday is 0, Sunday is 6
    if dt.weekday() >= 5:  # weekend
        return False
    if dt.hour < _BUSINESS_START_HOUR or dt.hour >= _BUSINESS_END_HOUR:
        return False
    return True


def _next_business_start(dt: datetime) -> datetime:
    """Return the next datetime at or after `dt` that falls on a business day at 9am."""
    # advance to next day if we're after business hours, or if it's weekend
    result = dt
    # if we're currently inside business hours, just return dt itself
    if _is_business_time(result):
        return result

    # move to the next possible start time
    result = result.replace(minute=0, second=0, microsecond=0)
    if result.hour >= _BUSINESS_END_HOUR:
        # start next calendar day at business start
        result = result + timedelta(days=1)
        result = result.replace(hour=_BUSINESS_START_HOUR)
    elif result.hour < _BUSINESS_START_HOUR:
        result = result.replace(hour=_BUSINESS_START_HOUR)

    # skip weekends
    while result.weekday() >= 5:
        result = result + timedelta(days=1)
        result = result.replace(hour=_BUSINESS_START_HOUR)
    return result


def _add_business_minutes(start: datetime, minutes: int) -> datetime:
    """Add a number of business minutes to `start`.

    Only time between 9:00 and 17:00 Monday–Friday is counted.
    """
    if minutes <= 0:
        return start

    current = start
    remaining = minutes

    # if start is not in a business window, jump to next start
    if not _is_business_time(current):
        current = _next_business_start(current)

    while remaining > 0:
        # end of current business day
        end_of_day = current.replace(hour=_BUSINESS_END_HOUR, minute=0, second=0, microsecond=0)
        chunk = int((end_of_day - current).total_seconds() / 60)
        if chunk <= 0:
            # move to next business day start and continue
            current = _next_business_start(current + timedelta(days=1))
            continue

        if remaining <= chunk:
            current = current + timedelta(minutes=remaining)
            remaining = 0
        else:
            remaining -= chunk
            # advance to next business day at start
            current = _next_business_start(end_of_day + timedelta(seconds=1))

    return current


def apply_sla_on_create(ticket: Ticket) -> None:
    """Set initial SLA deadlines on ticket creation.

    P1 tickets run 24/7 using the raw minute values in the SLA policy.
    P2–P4 tickets use a 9–17 business-day clock; the policy still stores
    the target in minutes, but only business minutes are counted when
    computing the deadline.
    """
    if not ticket.sla_policy:
        return

    created_at = ticket.created_at or _now()
    ticket.created_at = created_at

    # decide whether to apply business‑time rules (P1 is 24/7 only)
    use_business = ticket.priority in {"P2", "P3", "P4"}

    resp_min = ticket.sla_policy.response_target_minutes
    resl_min = ticket.sla_policy.resolution_target_minutes

    if use_business:
        ticket.response_due_at = _add_business_minutes(created_at, resp_min)
        ticket.resolution_due_at = _add_business_minutes(created_at, resl_min)
    else:
        ticket.response_due_at = created_at + timedelta(minutes=resp_min)
        ticket.resolution_due_at = created_at + timedelta(minutes=resl_min)


def _effective_deadlines(ticket: Ticket) -> tuple[Optional[datetime], Optional[datetime]]:
    pause = timedelta(seconds=ticket.total_pause_duration_seconds or 0)
    response_due = ticket.response_due_at + pause if ticket.response_due_at else None
    resolution_due = ticket.resolution_due_at + pause if ticket.resolution_due_at else None
    return response_due, resolution_due
from datetime import datetime, timezone, timedelta

def get_effective_deadlines(ticket: 'Ticket', now: Optional[datetime] = None):
    """Return data useful for UI: effective deadlines and time deltas."""
    
    # 1. Ensure 'now' is a timezone-aware UTC datetime
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Get deadlines from your helper function
    response_deadline, resolution_deadline = _effective_deadlines(ticket)

    def _delta(deadline: Optional[datetime]) -> Optional[timedelta]:
        if not deadline:
            return None
        
        # 2. Ensure the 'deadline' from the DB is also aware before subtraction
        # This prevents the "can't subtract offset-naive and offset-aware" error
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
            
        return deadline - now

    return {
        "response_deadline": response_deadline,
        "resolution_deadline": resolution_deadline,
        "response_delta": _delta(response_deadline),
        "resolution_delta": _delta(resolution_deadline),
    }


def update_pause_on_status_change(ticket: Ticket, new_status: str, now: Optional[datetime] = None) -> None:
    """Update pause-related fields when status changes."""
    now = now or _now()
    new_status = (new_status or "").lower()

    if new_status == "on_hold":
        # Entering On Hold: start pause window if not already started
        if ticket.on_hold_started_at is None:
            ticket.on_hold_started_at = now
    else:
        # Leaving On Hold: accumulate pause time
        if ticket.on_hold_started_at is not None:
            pause_delta = now - ticket.on_hold_started_at
            ticket.total_pause_duration_seconds = (ticket.total_pause_duration_seconds or 0) + int(
                pause_delta.total_seconds()
            )
            ticket.on_hold_started_at = None


def record_first_response_if_needed(ticket: Ticket, now: Optional[datetime] = None) -> None:
    """Set first_response_at if not already set."""
    if ticket.first_response_at is None:
        ticket.first_response_at = now or _now()


def record_resolved_if_needed(ticket: Ticket, now: Optional[datetime] = None) -> None:
    """Set resolved_at if not already set."""
    if ticket.resolved_at is None:
        ticket.resolved_at = now or _now()


def refresh_breach_flags(ticket: Ticket, now: Optional[datetime] = None) -> None:
    """Recalculate SLA breach flags based on current state."""
    now = now or _now()
    response_deadline, resolution_deadline = _effective_deadlines(ticket)

    # Response breach
    if response_deadline:
        if ticket.first_response_at:
            ticket.response_breached = ticket.first_response_at > response_deadline
        else:
            ticket.response_breached = now > response_deadline

    # Resolution breach
    if resolution_deadline:
        if ticket.resolved_at:
            ticket.resolution_breached = ticket.resolved_at > resolution_deadline
        else:
            ticket.resolution_breached = now > resolution_deadline

