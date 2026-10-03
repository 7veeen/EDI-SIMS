from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.shipment_service import (
    get_shipments,
    get_shipment_by_id,
    create_shipment,
    update_shipment_details,
    update_shipment_status,
    assign_employee
)

shipments_bp = Blueprint(
    "team2_shipments",
    __name__,
    url_prefix="/api/shipments"
)


# List Shipments (Supplier sees own only; Owner/Manager see all; Employee read-only)
@shipments_bp.route("/", methods=["GET"])
@shipments_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Supplier", "Employee")
def list_shipments():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    po_id = request.args.get("po_id") or request.args.get("purchase_order_id")
    supplier_id = request.args.get("supplier_id")
    status = request.args.get("status")
    search = request.args.get("search")

    shipments, stats, error = get_shipments(
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
        "shipments": shipments,
        "stats": stats
    }), 200


# View Single Shipment Details
@shipments_bp.route("/<int:shipment_id>", methods=["GET"])
@role_required("Owner", "Manager", "Supplier", "Employee")
def view_shipment(shipment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    shipment, error = get_shipment_by_id(
        shipment_id=shipment_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        if "Access denied" in error:
            return jsonify({
                "error": "Access denied",
                "message": "You can only view shipments associated with your supplier profile"
            }), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"shipment": shipment}), 200


# Create Shipment (Supplier creates for own accepted PO; Owner/Manager can also dispatch)
@shipments_bp.route("/", methods=["POST"])
@shipments_bp.route("", methods=["POST"])
@role_required("Supplier", "Owner", "Manager")
def add_shipment():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username", "Supplier")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    shipment, error = create_shipment(
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
        "message": "Shipment created successfully",
        "shipment": shipment
    }), 201


# Update Shipment Details (Carrier, Tracking, Package Count, Notes, etc.)
@shipments_bp.route("/<int:shipment_id>", methods=["PUT", "PATCH"])
@role_required("Supplier", "Owner", "Manager")
def edit_shipment(shipment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    shipment, error = update_shipment_details(
        shipment_id=shipment_id,
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
        "message": "Shipment details updated successfully",
        "shipment": shipment
    }), 200


# Update Shipment Status (Dispatched, In Transit, Delivered, Delayed, Cancelled)
@shipments_bp.route("/<int:shipment_id>/status", methods=["PATCH", "POST"])
@role_required("Supplier", "Owner", "Manager")
def change_shipment_status(shipment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "status is required"}), 400

    location = data.get("location")
    notes = data.get("notes")

    result, error = update_shipment_status(
        shipment_id=shipment_id,
        new_status=new_status,
        location=location,
        notes=notes,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Invalid status transition" in error or "Invalid status" in error:
            return jsonify({"error": error}), 400
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify(result), 200


# Assign Employee to Shipment (Owner and Manager only)
@shipments_bp.route("/<int:shipment_id>/assign", methods=["PATCH", "POST"])
@role_required("Owner", "Manager")
def assign_shipment_employee(shipment_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    employee_id = data.get("employee_id")
    if employee_id is None or employee_id == "":
        return jsonify({"error": "employee_id is required"}), 400

    result, error = assign_employee(
        shipment_id=shipment_id,
        employee_id=employee_id,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if "not found" in error:
            return jsonify({"error": error}), 404
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Employee assigned successfully",
        "shipment": result
    }), 200

