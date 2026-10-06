from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt

from app.services.team1.user_service import (
    create_user,
    get_users,
    get_user_by_id,
    update_user_status
)
from app.middleware.team1_auth import role_required


users_bp = Blueprint(
    "team1_users",
    __name__,
    url_prefix="/api/users"
)


@users_bp.route("/", methods=["POST"])
@role_required("Owner", "Manager")
def create_new_user():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role_name = data.get("role")

    if not username or not email or not password or not role_name:
        return jsonify({
            "error": "Username, email, password and role are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters long"
        }), 400

    claims = get_jwt()
    creator_role = claims.get("role")

    user, error = create_user(
        username,
        email,
        password,
        role_name,
        creator_role
    )

    if error:
        if error == "Database error":
            return jsonify({
                "error": error
            }), 500

        return jsonify({
            "error": error
        }), 400

    return jsonify({
        "message": "User created successfully",
        "user": user
    }), 201

@users_bp.route("/", methods=["GET"])
@role_required("Owner", "Manager")
def get_users_list():
    role_name = request.args.get("role")
    search = request.args.get("search")
    page = request.args.get("page")
    page_size = request.args.get("page_size")
    sort_by = request.args.get("sort_by")
    sort_order = request.args.get("sort_order")

    claims = get_jwt()
    creator_role = claims.get("role")

    if creator_role == "Manager" and role_name in ["Owner", "Manager"]:
        return jsonify({
            "error": "You do not have permission to view users with this role"
        }), 403

    users, total, error = get_users(
        creator_role=creator_role,
        role_name=role_name,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    if error:
        if error == "You do not have permission to view users with this role":
            return jsonify({
                "error": error
            }), 403
        return jsonify({
            "error": error
        }), 500

    response_data = {
        "users": users,
        "total": total
    }

    if page is not None:
        try:
            p_num = max(1, int(page))
        except (ValueError, TypeError):
            p_num = 1
        try:
            ps_num = max(1, min(100, int(page_size or 10)))
        except (ValueError, TypeError):
            ps_num = 10

        total_pages = (total + ps_num - 1) // ps_num if total > 0 else 1
        response_data["page"] = p_num
        response_data["page_size"] = ps_num
        response_data["total_pages"] = total_pages

    return jsonify(response_data), 200

@users_bp.route("/<int:user_id>", methods=["GET"])
@role_required("Owner", "Manager")
def get_user(user_id):
    user, error = get_user_by_id(user_id)

    if error:
        if error == "User not found":
            return jsonify({
                "error": error
            }), 404

        return jsonify({
            "error": error
        }), 500

    claims = get_jwt()
    creator_role = claims.get("role")

    if creator_role == "Manager" and user["role"] not in ["Employee", "Supplier"]:
        return jsonify({
            "error": "You do not have permission to view this user"
        }), 403

    return jsonify({
        "user": user
    }), 200

@users_bp.route("/<int:user_id>/status", methods=["PUT"])
@role_required("Owner", "Manager")
def change_user_status(user_id):
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    status = data.get("status")

    if status not in ["Active", "Inactive"]:
        return jsonify({
            "error": "Status must be either Active or Inactive"
        }), 400

    claims = get_jwt()
    creator_role = claims.get("role")
    current_user_id = int(get_jwt()["sub"])

    if current_user_id == user_id:
        return jsonify({
            "error": "You cannot change your own account status"
        }), 403

    target_user, error = get_user_by_id(user_id)

    if error:
        if error == "User not found":
            return jsonify({
                "error": error
            }), 404

        return jsonify({
            "error": error
        }), 500

    if creator_role == "Manager" and target_user["role"] not in [
        "Employee",
        "Supplier"
    ]:
        return jsonify({
            "error": "You do not have permission to change this user's status"
        }), 403

    updated_user, error = update_user_status(user_id, status)

    if error:
        return jsonify({
            "error": error
        }), 500

    return jsonify({
        "message": "User status updated successfully",
        "user": updated_user
    }), 200