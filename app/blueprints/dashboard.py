from flask import Blueprint, render_template

from ..services import kpi
from ..services.auth import login_required, role_required


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", methods=["GET"])
@login_required
@role_required("manager")
def index():
    sla_compliance = kpi.get_sla_compliance_rate()
    breached_counts = kpi.get_breached_counts()
    avg_response = kpi.get_avg_response_time_minutes()
    avg_resolution = kpi.get_avg_resolution_time_minutes()
    by_priority = kpi.get_ticket_counts_by_priority()
    by_type = kpi.get_ticket_counts_by_type()

    return render_template(
        "dashboard/index.html",
        sla_compliance=sla_compliance,
        breached_counts=breached_counts,
        avg_response=avg_response,
        avg_resolution=avg_resolution,
        by_priority=by_priority,
        by_type=by_type,
    )

