from flask import Blueprint, jsonify, request
from app.middleware.team1_auth import role_required
from app.services.team1.product_service import (
    get_products,
    get_product_by_id,
    create_product,
    update_product,
    delete_product
)

products_bp = Blueprint(
    "team1_products",
    __name__,
    url_prefix="/api/products"
)


# View/Search Products
@products_bp.route("/", methods=["GET"])
@products_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def list_products():
    search = request.args.get("search")
    category_id = request.args.get("category_id")
    status = request.args.get("status")

    if category_id:
        try:
            category_id = int(category_id)
        except ValueError:
            return jsonify({"error": "category_id must be an integer"}), 400

    products, error = get_products(search=search, category_id=category_id, status=status)

    if error:
        return jsonify({"error": error}), 500

    return jsonify({"products": products}), 200


# View Single Product
@products_bp.route("/<int:product_id>", methods=["GET"])
@role_required("Owner", "Manager", "Employee")
def view_product(product_id):
    product, error = get_product_by_id(product_id)

    if error:
        if error == "Product not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    return jsonify({"product": product}), 200


# Create Product
@products_bp.route("/", methods=["POST"])
@products_bp.route("", methods=["POST"])
@role_required("Owner", "Manager")
def add_product():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_name = data.get("product_name")
    sku = data.get("sku")
    category_id = data.get("category_id")
    # Support both 'selling_price' and 'price'
    selling_price = data.get("selling_price") if "selling_price" in data else data.get("price")
    reorder_level = data.get("reorder_level", 10)
    initial_stock = data.get("initial_stock", 0)

    if not product_name or not sku or category_id is None or selling_price is None:
        return jsonify({
            "error": "product_name, sku, category_id, and price/selling_price are required"
        }), 400

    product, error = create_product(
        product_name=product_name,
        sku=sku,
        category_id=category_id,
        selling_price=selling_price,
        reorder_level=reorder_level,
        initial_stock=initial_stock
    )

    if error:
        if error in ["Product SKU already exists"]:
            return jsonify({"error": error}), 409
        if error in ["Category does not exist", "Invalid category ID", "Selling price must be greater than or equal to 0", "Reorder level must be greater than or equal to 0", "Product name cannot be empty", "SKU cannot be empty"]:
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Product created successfully",
        "product": product
    }), 201


# Update Product
@products_bp.route("/<int:product_id>", methods=["PUT"])
@role_required("Owner", "Manager")
def edit_product(product_id):
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_name = data.get("product_name")
    sku = data.get("sku")
    category_id = data.get("category_id")
    selling_price = data.get("selling_price") if "selling_price" in data else data.get("price")
    reorder_level = data.get("reorder_level")
    status = data.get("status")

    product, error = update_product(
        product_id=product_id,
        product_name=product_name,
        sku=sku,
        category_id=category_id,
        selling_price=selling_price,
        reorder_level=reorder_level,
        status=status
    )

    if error:
        if error == "Product not found":
            return jsonify({"error": error}), 404
        if error == "Product SKU already in use by another product":
            return jsonify({"error": error}), 409
        if error in ["Category does not exist", "Invalid category ID", "Selling price must be greater than or equal to 0", "Reorder level must be greater than or equal to 0", "Product name cannot be empty", "SKU cannot be empty", "Status must be either 'Active' or 'Inactive'"]:
            return jsonify({"error": error}), 400
        return jsonify({"error": error}), 500

    return jsonify({
        "message": "Product updated successfully",
        "product": product
    }), 200


# Delete / Deactivate Product
@products_bp.route("/<int:product_id>", methods=["DELETE"])
@role_required("Owner", "Manager")
def remove_product(product_id):
    success, error, action_taken = delete_product(product_id)

    if error:
        if error == "Product not found":
            return jsonify({"error": error}), 404
        return jsonify({"error": error}), 500

    if action_taken == "deactivated":
        return jsonify({
            "message": "Product has existing order or transaction records and was deactivated to preserve data integrity.",
            "status": "Inactive"
        }), 200

    return jsonify({
        "message": "Product deleted successfully"
    }), 200
