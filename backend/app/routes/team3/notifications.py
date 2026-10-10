from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.middleware.team1_auth import role_required
from app.services.team3.notification_service import (
    get_user_notifications,
    get_notification_by_id,
    get_unread_count,
    mark_notification_as_read,
    mark_all_as_read
)


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)


# 1. GET /api/notifications/ - List notifications strictly for authenticated user
@notifications_bp.route("/", methods=["GET"])
@notifications_bp.route("", methods=["GET"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def list_notifications():
    # User identity strictly derived from validated JWT token
    user_id = get_jwt_identity()

    # Client query parameters (client-provided user_id is strictly ignored)
    is_read_param = request.args.get("is_read")
    is_read = None
    if is_read_param is not None:
        is_read = is_read_param.lower() in ("true", "1")

    limit = request.args.get("limit")
    offset = request.args.get("offset")

    notifications, error, status_code = get_user_notifications(
        user_id=user_id,
        is_read=is_read,
        limit=limit,
        offset=offset
    )

    if error:
        return jsonify({"error": error}), status_code

    return jsonify(notifications), 200


# 2. GET /api/notifications/unread-count - Unread counter for authenticated user
@notifications_bp.route("/unread-count", methods=["GET"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def unread_count():
    user_id = get_jwt_identity()

    result, error, status_code = get_unread_count(user_id)
    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), 200


# 3. PATCH /api/notifications/read-all - Mark all own notifications as read
@notifications_bp.route("/read-all", methods=["PATCH", "POST"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def mark_all_read():
    user_id = get_jwt_identity()

    result, error, status_code = mark_all_as_read(user_id)
    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), 200


# 4. GET /api/notifications/<int:notification_id> - Single notification detail with IDOR check
@notifications_bp.route("/<int:notification_id>", methods=["GET"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def get_single_notification(notification_id):
    user_id = get_jwt_identity()

    notification, error, status_code = get_notification_by_id(notification_id, user_id)
    if error:
        return jsonify({"error": error}), status_code

    return jsonify(notification), 200


# 5. PATCH /api/notifications/<int:notification_id>/read - Mark single notification read with IDOR check
@notifications_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@role_required("Owner", "Manager", "Employee", "Supplier")
def mark_read(notification_id):
    user_id = get_jwt_identity()

    result, error, status_code = mark_notification_as_read(notification_id, user_id)
    if error:
        return jsonify({"error": error}), status_code

    return jsonify(result), 200