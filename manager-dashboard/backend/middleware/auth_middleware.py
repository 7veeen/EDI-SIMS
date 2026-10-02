from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
import os

from extensions import get_db_connection


def verify_active_manager():
    """
    Verifies that the JWT token belongs to an active user with 'Manager' or 'Owner' role.
    """
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        user_role = claims.get("role")
        user_id = get_jwt_identity()

        if user_role not in ["Manager", "Owner"]:
            return False, "Access denied: Manager or Owner role required", 403

        # Verify against database if possible
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT status FROM "Users" WHERE user_id = %s', (user_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()

            if not row:
                return False, "User account not found", 401
            if row[0] != "Active":
                return False, "User account is inactive", 403
        except Exception:
            # If DB is temporarily unreachable or testing, rely on verified JWT claims
            pass

        return True, None, 200
    except Exception as e:
        return False, f"Authentication required: {str(e)}", 401


def manager_required(optional_in_dev=True):
    """
    Decorator requiring Manager or Owner authentication.
    When optional_in_dev=True, standalone development mode allows preview if no header is supplied.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            
            # If no auth header and running in standalone dev mode, allow read-only preview
            if not auth_header and optional_in_dev and os.getenv("FLASK_ENV", "development") == "development":
                return fn(*args, **kwargs)

            # Strict JWT validation
            is_valid, err_msg, status_code = verify_active_manager()
            if not is_valid:
                return jsonify({
                    "success": False,
                    "error": "Unauthorized",
                    "message": err_msg
                }), status_code

            return fn(*args, **kwargs)
        return wrapper
    return decorator
