from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import get_db_connection

notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)

@notifications_bp.route("/", methods=["GET"])
@jwt_required()
def get_notifications():
    current_user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT
                notification_id,
                user_id,
                title,
                message,
                notification_type,
                is_read,
                created_at
            FROM "Notifications"
            WHERE user_id = %s
            ORDER BY notification_id DESC
        ''', (current_user_id,))

        rows = cursor.fetchall()

        notifications = []

        for row in rows:
            notifications.append({
                "notification_id": row[0],
                "user_id": row[1],
                "title": row[2],
                "message": row[3],
                "notification_type": row[4],
                "is_read": row[5],
                "created_at": row[6]
            })

        return jsonify(notifications), 200

    finally:
        cursor.close()
        conn.close()


@notifications_bp.route("/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_notification_as_read(notification_id):
    current_user_id = get_jwt_identity()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE "Notifications"
            SET is_read = TRUE
            WHERE notification_id = %s AND user_id = %s
            RETURNING notification_id, is_read
        ''', (notification_id, current_user_id))

        updated_notification = cursor.fetchone()

        if updated_notification is None:
            conn.rollback()
            return jsonify({
                "error": "Notification not found"
            }), 404

        conn.commit()

        return jsonify({
            "notification_id": updated_notification[0],
            "is_read": updated_notification[1]
        }), 200

    finally:
        cursor.close()
        conn.close()