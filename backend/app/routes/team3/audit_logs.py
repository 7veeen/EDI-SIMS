from flask import Blueprint, jsonify, request

from app.middleware.team1_auth import role_required
from app.services.team3.audit_service import get_all_audit_logs


audit_logs_bp = Blueprint(
    "audit_logs",
    __name__,
    url_prefix="/api/audit-logs"
)


@audit_logs_bp.route("/", methods=["GET"])
@audit_logs_bp.route("", methods=["GET"])
@role_required("Owner")
def get_audit_logs():
    page = request.args.get("page", default=1)
    limit = request.args.get("page_size") or request.args.get("limit", default=50)
    search = request.args.get("search")
    action = request.args.get("action")
    table_name = request.args.get("table_name")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    result, error = get_all_audit_logs(
        limit=limit,
        page=page,
        search=search,
        action=action,
        table_name=table_name,
        start_date=start_date,
        end_date=end_date
    )
    if error:
        if any(kw in error.lower() for kw in ["invalid", "cannot be after", "must be"]):
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify(result), 200
