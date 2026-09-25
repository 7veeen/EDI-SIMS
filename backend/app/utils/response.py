from flask import jsonify
from typing import Any, Optional

def success_response(data: Any = None, message: str = "Success", status_code: int = 200, **kwargs):
    """Standard success API response JSON envelope."""
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {}
    }
    payload.update(kwargs)
    return jsonify(payload), status_code

def error_response(message: str = "An error occurred", error: Optional[Any] = None, status_code: int = 400, **kwargs):
    """Standard error API response JSON envelope."""
    payload = {
        "success": False,
        "message": message,
        "error": error if error is not None else message
    }
    payload.update(kwargs)
    return jsonify(payload), status_code
