from functools import wraps
from typing import Iterable, Optional

from flask import flash, redirect, request, session, url_for, g

from ..models import User
from .. import db


def get_current_user() -> Optional[User]:
    if "user" not in g:
        user_id = session.get("user_id")
        if not user_id:
            g.user = None
        else:
            g.user = db.session.get(User, user_id)
    return g.user


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not get_current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles: Iterable[str]):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if roles and user.role not in roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("tickets.ticket_dashboard"))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator

