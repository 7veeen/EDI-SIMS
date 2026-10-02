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

    claims = get_jwt()
    creator_role = claims.get("role")

    if role_name:
        allowed_roles = {
            "Owner": ["Owner", "Manager", "Employee", "Supplier"],
            "Manager": ["Employee", "Supplier"]
        }

        if role_name not in allowed_roles[creator_role]:
            return jsonify({
                "error": "You do not have permission to view users with this role"
            }), 403

    users, error = get_users(
        role_name=role_name,
        search=search
    )

    if error:
        return jsonify({
            "error": error
        }), 500

    return jsonify({
        "users": users
    }), 200

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

from app.services.team1.user_service import update_username
from flask_jwt_extended import jwt_required

@users_bp.route("/me/username", methods=["PUT"])
@jwt_required()
def change_own_username():
    data = request.get_json()

    if not data:
        return jsonify({
            "error": "Request body is required"
        }), 400

    new_username = data.get("username")

    if not new_username:
        return jsonify({
            "error": "New username is required"
        }), 400

    current_user_id = int(get_jwt()["sub"])

    updated_user, error = update_username(current_user_id, new_username)

    if error:
        if error == "Username already taken":
            return jsonify({
                "error": error
            }), 409
        
        return jsonify({
            "error": error
        }), 500

    return jsonify({
        "message": "Username updated successfully",
        "user": updated_user
    }), 200