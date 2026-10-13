from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.supplier_invoice_service import (
    submit_invoice,
    get_invoices,
    get_invoice_by_id,
    approve_invoice,
    reject_invoice,
    cancel_invoice
)

invoices_bp = Blueprint(
    "team2_invoices",
    __name__,
    url_prefix="/api/invoices"
)


# 1. Submit Invoice (Supplier only)
@invoices_bp.route("", methods=["POST"])
@invoices_bp.route("/", methods=["POST"])
@role_required("Supplier")
def create_invoice():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result, error, status_code = submit_invoice(
        user_id=user_id,
        role=user_role,
        data=data
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify({
        "message": "Invoice submitted successfully",
        "invoice": result
    }), status_code


# 2. List Invoices (Owner/Manager see all; Supplier sees own only; Employee denied)
@invoices_bp.route("", methods=["GET"])
@invoices_bp.route("/", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def list_invoices():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    status = request.args.get("status")
    supplier_id_filter = request.args.get("supplier_id")
    po_id = request.args.get("po_id") or request.args.get("purchase_order_id")
    date_from = request.args.get("date_from") or request.args.get("start_date")
    date_to = request.args.get("date_to") or request.args.get("end_date")
    search = request.args.get("search")
    page = request.args.get("page", 1)
    limit = request.args.get("page_size") or request.args.get("limit", 50)

    result, error, status_code = get_invoices(
        user_id=user_id,
        role=user_role,
        status=status,
        supplier_id_filter=supplier_id_filter,
        po_id=po_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        page=page,
        limit=limit
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 3. Retrieve Single Invoice Details
@invoices_bp.route("/<int:invoice_id>", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def view_invoice(invoice_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    result, error, status_code = get_invoice_by_id(
        invoice_id=invoice_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 4. Approve Invoice (Owner and Manager only)
@invoices_bp.route("/<int:invoice_id>/approve", methods=["PATCH", "POST"])
@role_required("Owner", "Manager")
def approve_invoice_route(invoice_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    result, error, status_code = approve_invoice(
        invoice_id=invoice_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 5. Reject Invoice (Owner and Manager only with mandatory reason)
@invoices_bp.route("/<int:invoice_id>/reject", methods=["PATCH", "POST"])
@role_required("Owner", "Manager")
def reject_invoice_route(invoice_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True) or {}
    rejection_reason = data.get("rejection_reason") or data.get("reason")

    if not rejection_reason or not str(rejection_reason).strip():
        return jsonify({"error": "rejection_reason is required when rejecting an invoice"}), 400

    result, error, status_code = reject_invoice(
        invoice_id=invoice_id,
        user_id=user_id,
        role=user_role,
        rejection_reason=rejection_reason
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 6. Cancel Invoice (Supplier for Submitted; Owner/Manager for zero-payment invoices)
@invoices_bp.route("/<int:invoice_id>/cancel", methods=["PATCH", "POST"])
@role_required("Owner", "Manager", "Supplier")
def cancel_invoice_route(invoice_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True) or {}
    reason = data.get("reason") or data.get("notes")

    result, error, status_code = cancel_invoice(
        invoice_id=invoice_id,
        user_id=user_id,
        role=user_role,
        reason=reason
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), status_code


# 7. Retrieve Payment History for Invoice
@invoices_bp.route("/<int:invoice_id>/payments", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def view_invoice_payments(invoice_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    result, error, status_code = get_invoice_by_id(
        invoice_id=invoice_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        return jsonify({"error": error}), status_code

    inv = result.get("invoice", {})
    return jsonify({
        "invoice_id": inv.get("invoice_id"),
        "invoice_number": inv.get("invoice_number"),
        "total_amount": inv.get("total_amount"),
        "total_paid": inv.get("total_paid"),
        "remaining_balance": inv.get("remaining_balance"),
        "payment_count": inv.get("payment_count"),
        "payments": inv.get("payments", [])
    }), 200
