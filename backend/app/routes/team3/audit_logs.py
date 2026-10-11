from flask import Blueprint, jsonify

from app.middleware.team1_auth import role_required
from app.services.team3.audit_service import get_all_audit_logs


audit_logs_bp = Blueprint(
    "audit_logs",
    __name__,
    url_prefix="/api/audit-logs"
)


@audit_logs_bp.route("/", methods=["GET"])
@role_required("Owner")
def get_audit_logs():
    logs, error = get_all_audit_logs()
    if error:
        return jsonify({"error": error}), 500
    return jsonify(logs), 200