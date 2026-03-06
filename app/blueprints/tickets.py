from datetime import datetime, timezone
import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db
from ..models import Ticket, TicketComment, User
from ..services.tickets import (
    calculate_priority,
    get_sla_policy_for_priority,
    transition_status,
)
from ..services.sla import apply_sla_on_create, get_effective_deadlines
from ..services.auth import get_current_user, login_required, role_required


tickets_bp = Blueprint("tickets", __name__, url_prefix="/tickets")


@tickets_bp.route("/", methods=["GET"])
@login_required
@role_required("agent", "manager")
def ticket_dashboard():
    """Combined dashboard for agents and managers with appropriate scopes/views."""
    user = get_current_user()
    query = Ticket.query
    unassigned_flag = False

    # filtering parameters
    priority = request.args.get("priority") or None
    status = request.args.get("status") or None
    issue_type = request.args.get("issue_type") or None
    sla_filter = request.args.get("sla") or None  # values: breached, within

    # determine scope/view without extra filters or sorting
    if user.role == "agent":
        view = request.args.get("view") or "my"
        if view == "all":
            # show unassigned tickets only
            query = query.filter(Ticket.assignee_id == None)
            unassigned_flag = True
        else:
            # my tickets: assigned to me or created by me
            query = query.filter(
                (Ticket.assignee_id == user.id) | (Ticket.created_by_id == user.id)
            )
        selected_view = view
        selected_scope = None
    else:  # manager
        view = request.args.get("view") or "my"
        # allow filtering unassigned when viewing all
        if view == "all":
            if request.args.get("unassigned") == "1":
                query = query.filter(Ticket.assignee_id == None)
                unassigned_flag = True
        else:  # my issues
            query = query.filter(
                (Ticket.created_by_id == user.id) | (Ticket.assigned_by_id == user.id)
            )
        selected_view = view
        selected_scope = None

    # apply common filters
    # agent in "all" view should not see SLA options
    if priority:
        query = query.filter(Ticket.priority == priority)
    if status:
        query = query.filter(Ticket.status == status)
    if issue_type:
        query = query.filter(Ticket.issue_type == issue_type)
    if sla_filter and not (user.role == "agent" and selected_view == "all"):
        if sla_filter == "breached":
            query = query.filter(Ticket.resolution_breached == True)
        elif sla_filter == "within":
            query = query.filter(Ticket.resolution_breached == False)

    # default ordering
    query = query.order_by(Ticket.created_at.desc())
    tickets = query.all()

    now = datetime.now(timezone.utc)
    sla_info = {t.id: get_effective_deadlines(t, now=now) for t in tickets}

    return render_template(
        "tickets/list.html",
        tickets=tickets,
        sla_info=sla_info,
        selected_priority=priority,
        selected_status=status,
        selected_issue_type=issue_type,
        selected_sla=sla_filter,
        selected_view=selected_view,
        show_unassigned=unassigned_flag,
    )


@tickets_bp.route("/new", methods=["GET", "POST"])
@login_required
@role_required("agent", "manager")
def create_ticket():
    # agent list is only needed for selection removal, can still show for info
    agents = User.query.filter_by(role="agent").all()
    current = get_current_user()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        issue_type = request.form.get("issue_type")

        impact = request.form.get("impact") or None
        urgency = request.form.get("urgency") or None
        system_affected = request.form.get("system_affected") or None

        request_category = request.form.get("request_category") or None
        department = request.form.get("department") or None
        approval_required = request.form.get("approval_required")
        approval_required_bool = approval_required == "yes"

        # new tickets are always unassigned initially
        assignee = None

        # creator should be the logged‑in user
        created_by = current

        if not title or not description or not issue_type:
            flash("Title, description, and issue type are required.", "danger")
            return render_template(
                "tickets/create.html",
                agents=agents,
            )

        priority = calculate_priority(issue_type, impact, urgency)
        sla_policy = get_sla_policy_for_priority(priority)
        if not sla_policy:
            flash("No SLA policy configured for the calculated priority.", "danger")
            return render_template(
                "tickets/create.html",
                agents=agents,
            )

        ticket = Ticket(
            title=title,
            description=description,
            issue_type=issue_type,
            impact=impact,
            urgency=urgency,
            system_affected=system_affected,
            request_category=request_category,
            department=department,
            approval_required=approval_required_bool if issue_type == "service_request" else None,
            priority=priority,
            sla_policy=sla_policy,
            status="new",
            assignee=None,
            created_by=created_by or agents[0] if agents else None,
        )

        # Phase 2: set SLA deadlines on creation
        apply_sla_on_create(ticket)

        db.session.add(ticket)
        db.session.commit()

        flash(f"Ticket #{ticket.id} created with priority {ticket.priority}.", "success")
        return redirect(url_for("tickets.ticket_dashboard"))

    return render_template(
        "tickets/create.html",
        agents=agents,
    )


@tickets_bp.route("/<int:ticket_id>", methods=["GET"])
@login_required
@role_required("agent", "manager")
def ticket_detail(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    agents = User.query.filter_by(role="agent").all()
    now = datetime.now(timezone.utc)
    sla_data = get_effective_deadlines(ticket, now=now)

    return render_template(
        "tickets/detail.html",
        ticket=ticket,
        agents=agents,
        sla_data=sla_data,
    )


@tickets_bp.route("/<int:ticket_id>/status", methods=["POST"])
@login_required
@role_required("agent", "manager")
def update_status(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    new_status = request.form.get("status")

    if not new_status:
        flash("No status provided.", "danger")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    try:
        transition_status(ticket, new_status)
        db.session.commit()
        flash(f"Status updated to {ticket.status}.", "success")
    except ValueError as exc:
        db.session.rollback()
        flash(str(exc), "danger")

    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/assign", methods=["POST"])
@login_required
@role_required("manager")
def assign_ticket(ticket_id: int):
    """Assign or unassign a ticket. Only managers can do this."""
    current_user = get_current_user()
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    assignee_id = request.form.get("assignee_id")

    old_assignee = ticket.assignee.name if ticket.assignee else "Unassigned"

    if not assignee_id:
        # Unassign the ticket
        ticket.assignee = None
        ticket.assigned_by = current_user
        db.session.commit()
        
        # Log the action
        logger = logging.getLogger("app.manager")
        extra = {"user": current_user.email if current_user else "unknown"}
        logger.info(f"Unassigned Ticket #{ticket.id} - {ticket.title}: {old_assignee} → Unassigned", extra=extra)
        
        flash("Ticket unassigned.", "success")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    assignee = db.session.get(User, assignee_id)
    if not assignee or assignee.role != "agent":
        flash("Invalid agent selected.", "danger")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    ticket.assignee = assignee
    ticket.assigned_by = current_user
    db.session.commit()
    
    # Log the action
    logger = logging.getLogger("app.manager")
    extra = {"user": current_user.email if current_user else "unknown"}
    logger.info(f"Assigned Ticket #{ticket.id} - {ticket.title}: {old_assignee} → {assignee.name}", extra=extra)
    
    flash(f"Ticket assigned to {assignee.name}.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))



@tickets_bp.route("/<int:ticket_id>/take", methods=["POST"])
@login_required
@role_required("agent")
def take_ticket(ticket_id: int):
    """Allow an agent to claim an unassigned ticket."""
    current_user = get_current_user()
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    if ticket.assignee_id:
        flash("Ticket is already assigned.", "danger")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    ticket.assignee = current_user
    ticket.assigned_by = current_user
    db.session.commit()
    flash("You have been assigned to this ticket.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@tickets_bp.route("/<int:ticket_id>/comments", methods=["POST"])
@login_required
@role_required("agent", "manager")
def add_comment(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    body = (request.form.get("body") or "").strip()

    if not body:
        flash("Comment cannot be empty.", "danger")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    current_user = get_current_user()

    comment = TicketComment(ticket=ticket, author=current_user, body=body)
    db.session.add(comment)
    db.session.commit()

    flash("Comment added.", "success")
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))
