from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.supplier_payment_service import (
    record_payment,
    get_payments,
    get_payment_by_id
)

payments_bp = Blueprint(
    "team2_payments",
    __name__,
    url_prefix="/api/payments"
)


# 1. Record Payment Disbursement (Owner and Manager only)
@payments_bp.route("", methods=["POST"])
@payments_bp.route("/", methods=["POST"])
@role_required("Owner", "Manager")
def create_payment():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result, error, status_code = record_payment(
        user_id=user_id,
        role=user_role,
        data=data
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify({
        "message": "Payment recorded successfully",
        "payment": result["payment"],
        "invoice": result["invoice"]
    }), status_code


# 2. List Payments (Owner/Manager see all; Supplier sees own only; Employee denied)
@payments_bp.route("", methods=["GET"])
@payments_bp.route("/", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def list_payments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    supplier_id_filter = request.args.get("supplier_id")
    invoice_id_filter = request.args.get("invoice_id")
    payment_method_filter = request.args.get("payment_method")
    date_from = request.args.get("date_from") or request.args.get("start_date")
    date_to = request.args.get("date_to") or request.args.get("end_date")
    search = request.args.get("search")
    page = request.args.get("page", 1)
    limit = request.args.get("limit", 50)

    result, error, status_code = get_payments(
        user_id=user_id,
        role=user_role,
        supplier_id_filter=supplier_id_filter,
        invoice_id_filter=invoice_id_filter,
        payment_method_filter=payment_method_filter,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 3. Retrieve Single Payment Details
@payments_bp.route("/<int:payment_id>", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def view_payment(payment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    result, error, status_code = get_payment_by_id(
        payment_id=payment_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code
