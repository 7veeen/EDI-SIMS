from flask import Blueprint, jsonify, request, Response

from app.middleware.team1_auth import role_required
from app.services.team3.report_service import (
    check_inventory_status,
    get_reports_metadata,
    generate_inventory_report_record,
    generate_inventory_csv_export
)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.route("/", methods=["GET"])
def get_reports():
    reports, error, status_code = get_reports_metadata()
    if error:
        return jsonify(error), status_code

    return jsonify(reports), 200


@reports_bp.route("/status", methods=["GET"])
def get_inventory_status():
    status_info, error, status_code = check_inventory_status()
    if error:
        return jsonify(error), status_code

    return jsonify(status_info), 200


@reports_bp.route("/generate", methods=["POST"])
def generate_report():
    data = request.get_json(silent=True) or {}

    report_name = data.get("report_name")
    report_type = data.get("report_type")
    generated_by = data.get("generated_by")

    if not report_name or not report_type or not generated_by:
        return jsonify({
            "error": "report_name, report_type and generated_by are required"
        }), 400

    result, error, status_code = generate_inventory_report_record(
        report_name=report_name,
        report_type=report_type,
        generated_by=generated_by
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
