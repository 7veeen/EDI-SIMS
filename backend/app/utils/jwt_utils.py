import os
from functools import wraps

import jwt
from flask import jsonify, request


def token_required(function):
    @wraps(function)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        scheme, separator, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token.strip():
            return jsonify({"error": "A Bearer token is required"}), 401

        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            return jsonify({"error": "Authentication is not configured"}), 500

        try:
            payload = jwt.decode(token.strip(), secret, algorithms=["HS256"])
            user_id = payload.get("sub")
            if not user_id or not str(user_id).isdigit():
                raise jwt.InvalidTokenError("Missing or invalid subject")
            request.user_id = int(user_id)
            request.user_role = payload.get("role")
            request.user_email = payload.get("email")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token"}), 401

        return function(*args, **kwargs)

    return decorated


def role_required(*allowed_roles):
    def decorator(function):
        @wraps(function)
        @token_required
        def decorated(*args, **kwargs):
            if request.user_role not in allowed_roles:
                return jsonify({"error": "You are not authorized to perform this action"}), 403
            return function(*args, **kwargs)

        return decorated

    return decorator
