from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from werkzeug.security import generate_password_hash
import logging

from .. import db
from ..models import Ticket, User
from ..services.auth import role_required, get_current_user


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/agents", methods=["GET", "POST"])
@role_required("manager")
def manage_agents():
    current_user = get_current_user()
    
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "danger")
        else:
            user = User(
                name=name,
                email=email,
                role="agent",
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            
            # Log the action
            logger = logging.getLogger("app.manager")
            extra = {"user": current_user.email if current_user else "unknown"}
            logger.info(f"Created new agent: {name} ({email})", extra=extra)
            
            flash("Agent created.", "success")

    agents = User.query.filter_by(role="agent").order_by(User.created_at.desc()).all()
    return render_template("admin/agents.html", agents=agents)


@admin_bp.route("/tickets", methods=["GET"])
@role_required("manager")
def list_tickets():
    """Admin view: list all tickets, with optional unassigned filter."""
    from ..services.sla import get_effective_deadlines

    unassigned_flag = request.args.get("unassigned") == "1"

    query = Ticket.query
    if unassigned_flag:
        query = query.filter(Ticket.assignee_id == None)
    tickets = query.order_by(Ticket.created_at.desc()).all()

    # include SLA info only if needed by template (not strictly used here anymore)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sla_info = {t.id: get_effective_deadlines(t, now=now) for t in tickets}

    return render_template(
        "admin/tickets.html",
        tickets=tickets,
        show_unassigned=unassigned_flag,
    )


@admin_bp.route("/tickets/<int:ticket_id>/edit", methods=["GET", "POST"])
@role_required("manager")
def edit_ticket(ticket_id: int):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return render_template("404.html"), 404
    agents = User.query.filter_by(role="agent").all()
    current_user = get_current_user()

    if request.method == "POST":
        old_title = ticket.title
        old_priority = ticket.priority
        old_assignee = ticket.assignee.name if ticket.assignee else "Unassigned"
        
        ticket.title = (request.form.get("title") or "").strip()
        ticket.description = (request.form.get("description") or "").strip()
        ticket.priority = (request.form.get("priority") or ticket.priority).strip()

        assignee_id = request.form.get("assignee_id")
        ticket.assignee = db.session.get(User, assignee_id) if assignee_id else None
        # track who assigned
        ticket.assigned_by = current_user if assignee_id else None

        db.session.commit()
        
        # Log the changes
        logger = logging.getLogger("app.manager")
        extra = {"user": current_user.email if current_user else "unknown"}
        
        changes = []
        if old_title != ticket.title:
            changes.append(f"Title: '{old_title}' → '{ticket.title}'")
        if old_priority != ticket.priority:
            changes.append(f"Priority: {old_priority} → {ticket.priority}")
        new_assignee = ticket.assignee.name if ticket.assignee else "Unassigned"
        if old_assignee != new_assignee:
            changes.append(f"Assignee: {old_assignee} → {new_assignee}")
        
        if changes:
            change_summary = "; ".join(changes)
            logger.info(f"Updated Ticket #{ticket.id}: {change_summary}", extra=extra)
        
        flash("Ticket updated.", "success")
        return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))

    return render_template(
        "admin/ticket_edit.html",
        ticket=ticket,
        agents=agents,
    )

