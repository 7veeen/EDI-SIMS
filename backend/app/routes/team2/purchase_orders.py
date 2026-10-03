from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team2.purchase_order_service import (
    get_purchase_orders,
    get_purchase_order_by_id,
    create_purchase_order,
    respond_to_purchase_order
)

purchase_orders_bp = Blueprint(
    "team2_purchase_orders",
    __name__,
    url_prefix="/api/purchase-orders"
)


# List Purchase Orders with RBAC & Supplier Isolation
@purchase_orders_bp.route("/", methods=["GET"])
@purchase_orders_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def list_purchase_orders():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    search = request.args.get("search")
    status = request.args.get("status")
    supplier_id_filter = request.args.get("supplier_id")

    orders, stats, error = get_purchase_orders(
        user_id=user_id,
        role=user_role,
        search=search,
        status=status,
        supplier_id_filter=supplier_id_filter
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify({
        "purchase_orders": orders,
        "stats": stats
    }), 200


# View Single Purchase Order Details
@purchase_orders_bp.route("/<int:purchase_order_id>", methods=["GET"])
@role_required("Owner", "Manager", "Supplier")
def view_purchase_order(purchase_order_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")

    order, error = get_purchase_order_by_id(
        purchase_order_id=purchase_order_id,
        user_id=user_id,
        role=user_role
    )

    if error:
        if error == "Access denied":
            return jsonify({
                "error": "Access denied",
                "message": "You can only view purchase orders assigned to your supplier profile"
            }), 403
        if error == "Purchase order not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"purchase_order": order}), 200


# Create Purchase Order (Manager and Owner only)
@purchase_orders_bp.route("/", methods=["POST"])
@purchase_orders_bp.route("", methods=["POST"])
@role_required("Owner", "Manager")
def add_purchase_order():
    user_id = get_jwt_identity()
    claims = get_jwt()
    username = claims.get("username", "Manager")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    order, error = create_purchase_order(
        data=data,
        ordered_by_user_id=user_id,
        username=username
    )

    if error:
        if "does not exist" in error or "not found" in error:
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Purchase order created successfully",
        "purchase_order": order
    }), 201


# Supplier Accepts or Rejects Purchase Order
@purchase_orders_bp.route("/<int:purchase_order_id>/respond", methods=["PATCH", "PUT"])
@role_required("Supplier", "Owner", "Manager")
def respond_purchase_order(purchase_order_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    result, error = respond_to_purchase_order(
        purchase_order_id=purchase_order_id,
        response_data=data,
        user_id=user_id,
        role=user_role,
        username=username
    )

    if error:
        if error == "Access denied":
            return jsonify({
                "error": "Access denied",
                "message": "You can only respond to purchase orders assigned to your supplier profile"
            }), 403
        if error == "Purchase order not found":
            return jsonify({"error": error}), 404
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify(result), 200
