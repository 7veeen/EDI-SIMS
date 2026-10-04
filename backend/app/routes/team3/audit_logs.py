from flask import Blueprint, jsonify

from app.extensions import get_db_connection
from app.middleware.team1_auth import role_required


audit_logs_bp = Blueprint(
    "audit_logs",
    __name__,
    url_prefix="/api/audit-logs"
)


@audit_logs_bp.route("/", methods=["GET"])
@role_required("Owner")
def get_audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT
                log_id,
                user_id,
                action,
                table_name,
                record_id,
                action_time,
                ip_address
            FROM "AuditLogs"
            ORDER BY log_id DESC
        ''')

        rows = cursor.fetchall()

        audit_logs = []

        for row in rows:
            audit_logs.append({
                "log_id": row[0],
                "user_id": row[1],
                "action": row[2],
                "table_name": row[3],
                "record_id": row[4],
                "action_time": row[5],
                "ip_address": row[6]
            })

        return jsonify(audit_logs), 200

    finally:
        cursor.close()
        conn.close()