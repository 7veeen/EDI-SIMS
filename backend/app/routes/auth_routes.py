import logging
import os
from datetime import datetime, timedelta, timezone

import jwt
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash

from app.config.supabase_client import supabase

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "A JSON request body is required"}), 400

    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        logger.error("JWT_SECRET_KEY is not configured")
        return jsonify({"error": "Authentication is not configured"}), 500

    try:
        response = (supabase.table("Users")
                    .select("user_id, username, email, password_hash, role_id, status")
                    .eq("email", email).maybe_single().execute())
        user = response.data
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid login credentials"}), 401
        if user.get("status") != "Active":
            return jsonify({"error": "User account is inactive"}), 403

        role_response = (supabase.table("Roles").select("role_name")
                         .eq("role_id", user["role_id"]).maybe_single().execute())
        if not role_response.data:
            return jsonify({"error": "User role is unavailable"}), 403

        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        token = jwt.encode({
            "sub": str(user["user_id"]), "email": user["email"],
            "username": user["username"], "role": role_response.data["role_name"],
            "exp": expires_at,
        }, secret, algorithm="HS256")
        return jsonify({
            "message": "Login successful", "access_token": token,
            "token_type": "Bearer", "expires_in": 7200,
            "user": {"user_id": user["user_id"], "username": user["username"],
                     "email": user["email"], "role": role_response.data["role_name"]},
        }), 200
    except Exception:
        logger.exception("Login failed while accessing the authentication store")
        return jsonify({"error": "Unable to authenticate at this time"}), 500
