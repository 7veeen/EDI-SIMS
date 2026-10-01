from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity

from app.services.team3.dashboard_service import (
    get_employee_dashboard,
    get_supplier_dashboard,
    get_manager_dashboard,
    get_owner_dashboard
)
from app.middleware.team1_auth import role_required


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard"
)


@dashboard_bp.route("/employee", methods=["GET"])
@role_required("Employee")
def employee_dashboard():
    user_id = get_jwt_identity()
    dashboard_data = get_employee_dashboard(user_id)

    return jsonify(dashboard_data), 200


@dashboard_bp.route("/supplier", methods=["GET"])
@role_required("Supplier")
def supplier_dashboard():
    dashboard_data = get_supplier_dashboard()

    return jsonify(dashboard_data), 200


@dashboard_bp.route("/manager", methods=["GET"])
@role_required("Manager")
def manager_dashboard():
    dashboard_data = get_manager_dashboard()

    return jsonify(dashboard_data), 200


@dashboard_bp.route("/owner", methods=["GET"])
@role_required("Owner")
def owner_dashboard():
    dashboard_data = get_owner_dashboard()

    return jsonify(dashboard_data), 200