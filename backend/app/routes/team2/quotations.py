from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.quotation_service import (
    get_quotations,
    get_quotation_by_id,
    create_quotation,
    update_draft_quotation,
    submit_quotation,
    approve_quotation,
    reject_quotation,
    compare_quotations_for_po
)

quotations_bp = Blueprint(
    "team2_quotations",
    __name__,
    url_prefix="/api/quotations"
)


# List Quotations (Supplier sees own only; Owner/Manager see all)
@quotations_bp.route("/", methods=["GET"])
@quotations_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def list_quotations():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    po_id = request.args.get("po_id") or request.args.get("purchase_order_id")
    supplier_id = request.args.get("supplier_id")
    status = request.args.get("status")
    search = request.args.get("search")

    quotes, stats, error = get_quotations(
        user_id=user_id,
        role=user_role,
        po_id=po_id,
        supplier_id_filter=supplier_id,
        status_filter=status,
        search=search
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify({
        "quotations": quotes,
        "stats": stats
    }), 200


# Compare Quotations for a Specific PO (Owner/Manager only)
@quotations_bp.route("/compare", methods=["GET"])
@role_required("Owner", "Manager")
def compare_quotations():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    po_id = request.args.get("po_id") or request.args.get("purchase_order_id")
    if not po_id:
        return jsonify({"error": "purchase_order_id query parameter is required"}), 400

    comparison, error = compare_quotations_for_po(
        purchase_order_id=po_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        if "not found" in error:
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"comparison": comparison}), 200


# View Single Quotation Details
@quotations_bp.route("/<int:quotation_id>", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def view_quotation(quotation_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    quote, error = get_quotation_by_id(
        quotation_id=quotation_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        if "Access denied" in error:
            return jsonify({
                "error": "Access denied",
                "message": "You can only view quotations submitted by your supplier profile"
            }), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"quotation": quote}), 200


# Create Quotation (Supplier creates for own accepted PO; Owner/Manager can also test/create)
@quotations_bp.route("/", methods=["POST"])
@quotations_bp.route("", methods=["POST"])
@role_required("Supplier", "Owner", "Manager")
def add_quotation():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username", "Supplier")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result, error = create_quotation(
        data=data,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "does not belong" in error or "Access denied" in error:
            return jsonify({"error": error}), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Quotation created successfully",
        "quotation": result
    }), 201


# Edit Draft Quotation (Supplier can edit own Draft quotation only)
@quotations_bp.route("/<int:quotation_id>", methods=["PUT", "PATCH"])
@role_required("Supplier", "Owner", "Manager")
def edit_quotation(quotation_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result, error = update_draft_quotation(
        quotation_id=quotation_id,
        data=data,
        user_id=user_id,
        role=user_role
    )

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Draft quotation updated successfully",
        "quotation": result
    }), 200


# Submit Draft Quotation (Changes status to Submitted)
@quotations_bp.route("/<int:quotation_id>/submit", methods=["POST", "PATCH"])
@role_required("Supplier", "Owner", "Manager")
def submit_draft_quotation(quotation_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username", "Supplier")

    result, error = submit_quotation(
        quotation_id=quotation_id,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Quotation submitted successfully",
        "quotation": result
    }), 200


# Approve Quotation (Manager/Owner only)
@quotations_bp.route("/<int:quotation_id>/approve", methods=["POST", "PATCH"])
@role_required("Owner", "Manager")
def approve_single_quotation(quotation_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username", "Manager")

    result, error = approve_quotation(
        quotation_id=quotation_id,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Quotation approved successfully",
        "result": result
    }), 200


# Reject Quotation (Manager/Owner only)
@quotations_bp.route("/<int:quotation_id>/reject", methods=["POST", "PATCH"])
@role_required("Owner", "Manager")
def reject_single_quotation(quotation_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username", "Manager")

    data = request.get_json(silent=True) or {}
    reason = data.get("rejection_reason") or "Rejected by manager"

    result, error = reject_quotation(
        quotation_id=quotation_id,
        rejection_reason=reason,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Quotation rejected successfully",
        "result": result
    }), 200
