from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.services.team1.product_service import (
    create_product,
    get_products,
    update_product,
    delete_product
)
from app.middleware.team1_auth import role_required

products_bp = Blueprint(
    "team1_products",
    __name__,
    url_prefix="/api/products"
)

@products_bp.route("/", methods=["GET"])
@jwt_required()
def get_products_list():
    search = request.args.get("search")
    products, error = get_products(search)
    
    if error:
        return jsonify({"error": error}), 500
        
    return jsonify({"products": products}), 200

@products_bp.route("/", methods=["POST"])
@jwt_required()
@role_required("Owner", "Manager", "Employee")
def create_new_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_name = data.get("product_name")
    sku = data.get("sku")
    category_id = data.get("category_id")
    reorder_level = data.get("reorder_level", 10)
    price = data.get("price", 0.0)

    if not product_name or not sku or not category_id:
        return jsonify({"error": "Product name, SKU, and Category ID are required"}), 400

    product, error = create_product(product_name, sku, category_id, reorder_level, price)
    
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify({"message": "Product created successfully", "product": product}), 201

@products_bp.route("/<int:product_id>", methods=["PUT"])
@jwt_required()
@role_required("Owner", "Manager", "Employee")
def update_existing_product(product_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    product_name = data.get("product_name")
    sku = data.get("sku")
    category_id = data.get("category_id")
    reorder_level = data.get("reorder_level")
    price = data.get("price")
    status = data.get("status")

    if not product_name or not sku or not category_id or not status:
        return jsonify({"error": "Missing required fields"}), 400

    product, error = update_product(product_id, product_name, sku, category_id, reorder_level, price, status)
    
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify({"message": "Product updated successfully", "product": product}), 200

@products_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required()
@role_required("Owner", "Manager")
def delete_existing_product(product_id):
    success, error = delete_product(product_id)
    
    if error:
        return jsonify({"error": error}), 400
        
    return jsonify({"message": "Product deleted successfully"}), 200
