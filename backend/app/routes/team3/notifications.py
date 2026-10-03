from flask import Blueprint, jsonify

from app.extensions import get_db_connection


notifications_bp = Blueprint(
    "notifications",
    __name__,
    url_prefix="/api/notifications"
)


@notifications_bp.route("/", methods=["GET"])
def get_notifications():
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
            ORDER BY notification_id DESC
        ''')

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
def mark_notification_as_read(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE "Notifications"
            SET is_read = TRUE
            WHERE notification_id = %s
            RETURNING notification_id, is_read
        ''', (notification_id,))

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