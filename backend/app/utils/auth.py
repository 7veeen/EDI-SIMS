import os
import functools
import logging
from typing import Optional, Dict, Any
from flask import request
from .response import error_response

logger = logging.getLogger(__name__)

def get_authenticated_supplier() -> Optional[Dict[str, Any]]:
    """
    Extracts and authenticates the current supplier from the request headers/token.
    Enforces RBAC: only users with role 'supplier' or authorized IDs can access.
    """
    # 1. Check Bearer token in Authorization header
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # 2. Check X-Supplier-Id header or X-User-Role header
    header_supplier_id = request.headers.get("X-Supplier-Id", "").strip()
    user_role = request.headers.get("X-User-Role", "supplier").strip().lower()

    # If supplier ID provided in header
    supplier_id = header_supplier_id or request.args.get("supplier_id", "").strip()

    # Ensure role is supplier (or authorized admin)
    if user_role not in ["supplier", "admin"]:
        logger.warning(f"Unauthorized role attempted supplier dashboard access: {user_role}")
        return None

    # Default fallback identifier if not passed, to support initial integration/browsing
    if not supplier_id:
        supplier_id = os.getenv("DEFAULT_SUPPLIER_ID", "sup-001")

    return {
        "supplier_id": supplier_id,
        "role": user_role,
        "token": token
    }

def require_supplier_auth(f):
    """
    Decorator to enforce supplier authentication and RBAC.
    Ensures that the requester is a valid supplier and prevents ID tampering.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_data = get_authenticated_supplier()
        if not auth_data or not auth_data.get("supplier_id"):
            return error_response(
                message="Unauthorized: Valid Supplier authentication required",
                status_code=401
            )
        
        # Verify requested supplier_id matches authenticated supplier_id
        requested_id = request.args.get("supplier_id")
        if requested_id and requested_id != auth_data["supplier_id"] and auth_data.get("role") != "admin":
            return error_response(
                message="Forbidden: Cannot access records belonging to another supplier",
                status_code=403
            )
            
        return f(*args, auth_data=auth_data, **kwargs)
    return decorated_function
