from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.middleware.team1_auth import role_required
from app.services.team2.stock_request_service import (
    get_stock_requests,
    get_stock_request_by_id,
    create_stock_request,
    respond_to_stock_request
)

stock_requests_bp = Blueprint("stock_requests", __name__, url_prefix="/api/stock-requests")


@stock_requests_bp.route("/", methods=["GET"])
@jwt_required()
def list_stock_requests():
    """List stock requests with strict role-based access and supplier isolation."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    status = request.args.get("status")
    priority = request.args.get("priority")
    search = request.args.get("search")
    supplier_id = request.args.get("supplier_id")

    requests_list, error = get_stock_requests(
        user_id=user_id,
        role=role,
        status=status,
        priority=priority,
        search=search,
        supplier_id=supplier_id
    )

    if error:
        status_code = 403 if "Access denied" in error else 500
        return jsonify({"error": error}), status_code

    return jsonify({"stock_requests": requests_list}), 200


@stock_requests_bp.route("/<int:stock_request_id>", methods=["GET"])
@jwt_required()
def get_single_stock_request(stock_request_id):
    """Get single stock request details with supplier isolation."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    request_data, error = get_stock_request_by_id(
        stock_request_id=stock_request_id,
        user_id=user_id,
        role=role
    )

    if error:
        if "not found" in error.lower():
            return jsonify({"error": error}), 404
        if "access denied" in error.lower():
            return jsonify({"error": error}), 403
        return jsonify({"error": error}), 500

    return jsonify({"stock_request": request_data}), 200


@stock_requests_bp.route("/", methods=["POST"])
@role_required("Owner", "Manager")
def create_new_stock_request():
    """Create a new stock request. Restricted to Owner and Manager."""
    user_id = get_jwt_identity()
    data = request.get_json()

    created_request, error = create_stock_request(
        requested_by_user_id=user_id,
        data=data
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Stock request created successfully.",
        "stock_request": created_request
    }), 201


@stock_requests_bp.route("/<int:stock_request_id>/respond", methods=["PATCH", "POST"])
@role_required("Supplier", "Owner", "Manager")
def respond_stock_request(stock_request_id):
    """Supplier response to Stock Request (Accept or Reject)."""
    user_id = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    data = request.get_json()

    result, error = respond_to_stock_request(
        stock_request_id=stock_request_id,
        user_id=user_id,
        role=role,
        data=data
    )

    if error:
        if "not found" in error.lower():
            return jsonify({"error": error}), 404
        if "access denied" in error.lower():
            return jsonify({"error": error}), 403
        return jsonify({"error": error}), 400

    return jsonify(result), 200
