from flask import Blueprint, jsonify
from app.middleware.team1_auth import role_required
from app.services.team3.status_service import get_liveness, get_detailed_health

status_bp = Blueprint("status", __name__, url_prefix="/api/status")


@status_bp.route("/", methods=["GET"])
@status_bp.route("", methods=["GET"])
def check_liveness():
    """
    Public minimal backend liveness ping.
    Does not expose database details, credentials, or internal configuration.
    """
    return jsonify(get_liveness()), 200


@status_bp.route("/health", methods=["GET"])
@role_required("Owner", "Manager")
def check_detailed_health():
    """
    Protected system health and telemetry endpoint for Owner and Manager.
    Reports backend availability, database connectivity, query latency,
    module readiness states from SystemStatus, uptime, and overall health.
    """
    health_data, status_code = get_detailed_health()
    return jsonify(health_data), status_code
