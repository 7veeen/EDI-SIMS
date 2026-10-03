from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity
from app.middleware.team1_auth import role_required
from app.services.team1.inventory_service import (
    get_inventory,
    get_inventory_by_id,
    adjust_inventory,
    stock_in,
    stock_out,
    get_stock_transactions,
    get_stock_transaction_by_id
)

inventory_bp = Blueprint(
    "team1_inventory",
    __name__,
    url_prefix="/api/inventory"
)


# View/Search Inventory
@inventory_bp.route("/", methods=["GET"])
@inventory_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def list_inventory():
    search = request.args.get("search")
    status_filter = request.args.get("status")
    category_id = request.args.get("category_id")

    if category_id:
        try:
            category_id = int(category_id)
        except ValueError:
            return jsonify({"error": "category_id must be an integer"}), 400

    data, error = get_inventory(
        search=search,
        status_filter=status_filter,
        category_id=category_id
    )

    if error:
        return jsonify({"error": error}), 500

    return jsonify(data), 200


# View Single Inventory Record
@inventory_bp.route("/<int:inventory_id>", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def view_inventory_item(inventory_id):
    item, error = get_inventory_by_id(inventory_id)

    if error:
        if error == "Inventory record not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"inventory": item}), 200


# Update / Adjust Stock
@inventory_bp.route("/<int:inventory_id>", methods=["PUT"])
@role_required("Owner", "Manager")
def update_inventory_stock(inventory_id):
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Support 'quantity_available' or 'quantity'
    if "quantity_available" in data:
        new_quantity = data.get("quantity_available")
    elif "quantity" in data:
        new_quantity = data.get("quantity")
    elif "adjustment" in data:
        # Calculate adjustment based on current quantity
        adjustment_val = data.get("adjustment")
        try:
            adj = int(adjustment_val)
        except (ValueError, TypeError):
            return jsonify({"error": "Adjustment must be an integer"}), 400

        curr_item, curr_err = get_inventory_by_id(inventory_id)
        if curr_err:
            if curr_err == "Inventory record not found":
                return jsonify({"error": curr_err}), 404
            return jsonify({"error": curr_err}), 500

        adj_type = str(data.get("type", "ADD")).upper()
        if adj_type == "SUBTRACT":
            new_quantity = curr_item["quantity_available"] - adj
        else:
            new_quantity = curr_item["quantity_available"] + adj
    else:
        return jsonify({"error": "quantity_available, quantity, or adjustment is required"}), 400

    try:
        new_quantity = int(new_quantity)
        if new_quantity < 0:
            return jsonify({"error": "Inventory quantity cannot be negative"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Quantity must be an integer"}), 400

    user_id = None
    try:
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
    except Exception:
        pass

    notes = data.get("notes")

    result, error = adjust_inventory(
        inventory_id=inventory_id,
        new_quantity=new_quantity,
        user_id=user_id,
        notes=notes
    )

    if error:
        if error == "Inventory record not found":
            return jsonify({"error": error}), 404
        if error in ["Inventory quantity cannot be negative", "Invalid quantity provided"]:
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Inventory adjusted successfully",
        "inventory": result
    }), 200


# Stock-In / Goods Receipt
@inventory_bp.route("/stock-in", methods=["POST"])
@role_required("Owner", "Manager", "Employee")
def perform_stock_in():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    shipment_id = data.get("shipment_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity")
    notes = data.get("notes")

    result, error = stock_in(
        shipment_id=shipment_id,
        product_id=product_id,
        quantity=quantity,
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
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify(result), 200


# Stock-Out / Stock Reduction
@inventory_bp.route("/stock-out", methods=["POST"])
@role_required("Owner", "Manager", "Employee")
def perform_stock_out():
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role")
    username = claims.get("username")

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    product_id = data.get("product_id")
    quantity = data.get("quantity")
    reason = data.get("reason")
    notes = data.get("notes")

    result, error = stock_out(
        product_id=product_id,
        quantity=quantity,
        reason=reason,
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
        if "Database error" in error:
            return jsonify({"error": error}), 500
        return jsonify({"error": error}), 400

    return jsonify(result), 200


# List Stock Transactions History
@inventory_bp.route("/transactions", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def list_stock_transactions():
    claims = get_jwt()
    user_role = claims.get("role")

    product_id = request.args.get("product_id")
    tx_type = request.args.get("transaction_type") or request.args.get("type")
    date_from = request.args.get("date_from") or request.args.get("start_date")
    date_to = request.args.get("date_to") or request.args.get("end_date")
    user_id_filter = request.args.get("user_id")
    shipment_id_filter = request.args.get("shipment_id")

    transactions, error = get_stock_transactions(
        product_id=product_id,
        transaction_type=tx_type,
        date_from=date_from,
        date_to=date_to,
        user_id_filter=user_id_filter,
        shipment_id_filter=shipment_id_filter,
        role=user_role
    )

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        return jsonify({"error": error}), 500

    return jsonify({
        "transactions": transactions,
        "count": len(transactions)
    }), 200


# View Single Stock Transaction Details
@inventory_bp.route("/transactions/<int:transaction_id>", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def view_stock_transaction(transaction_id):
    claims = get_jwt()
    user_role = claims.get("role")

    tx, error = get_stock_transaction_by_id(transaction_id, role=user_role)

    if error:
        if "Access denied" in error:
            return jsonify({"error": error}), 403
        if "not found" in error:
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"transaction": tx}), 200

