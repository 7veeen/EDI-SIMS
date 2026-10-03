from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.supplier_service import (
    get_suppliers,
    get_supplier_by_id,
    get_supplier_by_user_id,
    get_available_supplier_users,
    create_supplier,
    update_supplier,
    delete_supplier
)

suppliers_bp = Blueprint(
    "team2_suppliers",
    __name__,
    url_prefix="/api/suppliers"
)


# List Suppliers (with optional search and status filter)
@suppliers_bp.route("/", methods=["GET"])
@suppliers_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def list_suppliers():
    search = request.args.get("search")
    status = request.args.get("status")
    fmt = request.args.get("format")

    suppliers, error = get_suppliers(search=search, status=status)

    if error:
        return jsonify({"error": error}), 500

    if fmt == "array":
        return jsonify(suppliers), 200

    return jsonify({"suppliers": suppliers}), 200


# Get Users eligible for linking to a Supplier account
@suppliers_bp.route("/users", methods=["GET"])
@role_required("Owner", "Manager")
def list_supplier_users():
    supplier_id = request.args.get("supplier_id")
    if supplier_id:
        try:
            supplier_id = int(supplier_id)
        except ValueError:
            supplier_id = None

    users, error = get_available_supplier_users(current_supplier_id=supplier_id)
    if error:
        return jsonify({"error": error}), 500

    return jsonify({"users": users}), 200


# Get current logged-in Supplier's profile (Phase 7 identity mapping)
@suppliers_bp.route("/me", methods=["GET"])
@role_required("Supplier", "Owner", "Manager")
def get_current_supplier():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    supplier, error = get_supplier_by_user_id(user_id)
    if error:
        if error == "No supplier profile linked to this user account":
            return jsonify({
                "error": error,
                "user_id": user_id,
                "role": user_role
            }), 404
        return jsonify({"error": error}), 500

    return jsonify({"supplier": supplier}), 200


# Get single supplier details
@suppliers_bp.route("/<int:supplier_id>", methods=["GET"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def view_supplier(supplier_id):
    claims = get_jwt()
    user_role = claims.get("role")

    # If role is Supplier, verify they can only view their own profile
    if user_role == "Supplier":
        user_id = get_jwt_identity()
        own_supplier, error = get_supplier_by_user_id(user_id)
        if error or not own_supplier or own_supplier["supplier_id"] != supplier_id:
            return jsonify({
                "error": "Access denied",
                "message": "Suppliers can only view their own supplier profile"
            }), 403

    supplier, error = get_supplier_by_id(supplier_id)
    if error:
        if error == "Supplier not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"supplier": supplier}), 200


# Create new supplier
@suppliers_bp.route("/", methods=["POST"])
@suppliers_bp.route("", methods=["POST"])
@role_required("Owner", "Manager")
def add_supplier():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    supplier, error = create_supplier(data)
    if error:
        if "already exists" in error or "already linked" in error:
            return jsonify({"error": error}), 409
        if "required" in error or "Invalid" in error or "Status must be" in error or "does not" in error:
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Supplier created successfully",
        "supplier": supplier
    }), 201


# Update supplier
@suppliers_bp.route("/<int:supplier_id>", methods=["PUT"])
@role_required("Owner", "Manager")
def edit_supplier(supplier_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    supplier, error = update_supplier(supplier_id, data)
    if error:
        if error == "Supplier not found":
            return jsonify({"error": error}), 404
        if "already exists" in error or "already linked" in error:
            return jsonify({"error": error}), 409
        if "required" in error or "Invalid" in error or "cannot be empty" in error or "Status must be" in error or "No fields" in error:
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Supplier updated successfully",
        "supplier": supplier
    }), 200


# Delete / Deactivate supplier
@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
@role_required("Owner", "Manager")
def remove_supplier(supplier_id):
    result, error = delete_supplier(supplier_id)
    if error:
        if error == "Supplier not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify(result), 200
