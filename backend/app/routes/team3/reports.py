from flask import Blueprint, jsonify, request, Response
from flask_jwt_extended import get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team3.report_service import (
    check_inventory_status,
    get_reports_metadata,
    generate_inventory_report_record,
    generate_inventory_csv_export
)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.route("/", methods=["GET"])
@reports_bp.route("", methods=["GET"])
@role_required("Owner", "Manager")
def get_reports():
    reports, error, status_code = get_reports_metadata()
    if error:
        return jsonify(error), status_code

    return jsonify(reports), 200


@reports_bp.route("/status", methods=["GET"])
@role_required("Owner", "Manager")
def get_inventory_status():
    status_info, error, status_code = check_inventory_status()
    if error:
        return jsonify(error), status_code

    return jsonify(status_info), 200


@reports_bp.route("/generate", methods=["POST"])
@role_required("Owner", "Manager")
def generate_report():
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 401

    data = request.get_json(silent=True) or {}

    report_name = data.get("report_name")
    report_type = data.get("report_type")

    if not report_name or not report_type:
        return jsonify({
            "error": "report_name and report_type are required"
        }), 400

    result, error, status_code = generate_inventory_report_record(
        report_name=report_name,
        report_type=report_type,
        generated_by=user_id
    )
    if error:
        return jsonify(error), status_code

    return jsonify(result), status_code


@reports_bp.route("/export", methods=["GET"])
@reports_bp.route("/export/csv", methods=["GET"])
@role_required("Owner", "Manager")
def export_reports_csv():
    report_type = request.args.get("report_type", "Inventory")

    result, error, status_code = generate_inventory_csv_export(report_type=report_type)
    if error:
        return jsonify(error), status_code

    csv_bytes, filename = result

    response = Response(
        csv_bytes,
        mimetype="text/csv",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
    return response, 200
