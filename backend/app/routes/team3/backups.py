import json
import os
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from psycopg2 import sql

from app.extensions import get_db_connection
from app.middleware.team1_auth import role_required


backups_bp = Blueprint(
    "backups",
    __name__,
    url_prefix="/api/backups"
)


def json_serializer(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return str(value)


@backups_bp.route("/", methods=["GET"])
@role_required("Owner")
def get_backups():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT
                backup_id,
                backup_name,
                backup_type,
                backup_date,
                backup_size,
                created_by,
                status
            FROM "BackupHistory"
            ORDER BY backup_id DESC
        ''')

        rows = cursor.fetchall()

        backups = []

        for row in rows:
            backups.append({
                "backup_id": row[0],
                "backup_name": row[1],
                "backup_type": row[2],
                "backup_date": row[3],
                "backup_size": row[4],
                "created_by": row[5],
                "status": row[6]
            })

        return jsonify(backups), 200

    finally:
        cursor.close()
        conn.close()


@backups_bp.route("/", methods=["POST"])
@role_required("Owner")
def create_backup():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        jwt_user_id = get_jwt_identity()
        data = request.get_json(silent=True) or {}
        created_by = data.get("created_by") or jwt_user_id

        if created_by is None:
            return jsonify({
                "error": "created_by is required"
            }), 400

        cursor.execute(
            'SELECT user_id FROM "Users" WHERE user_id = %s',
            (created_by,)
        )

        if cursor.fetchone() is None:
            return jsonify({
                "error": "Invalid user_id"
            }), 400

        # Get all user-created tables in the public schema
        cursor.execute('''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        ''')

        table_names = [row[0] for row in cursor.fetchall()]

        backup_data = {}

        # Export every public table
        for table_name in table_names:
            cursor.execute(
                sql.SQL('SELECT * FROM {}').format(
                    sql.Identifier(table_name)
                )
            )

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            table_records = []

            for row in rows:
                record = {}

                for column, value in zip(columns, row):
                    record[column] = json_serializer(value)

                table_records.append(record)

            backup_data[table_name] = table_records

        # Create backup directory
        backup_directory = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "backups"
)

        os.makedirs(backup_directory, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        backup_name = f"inventory_backup_{timestamp}.json"
        backup_path = os.path.join(
            backup_directory,
            backup_name
        )

        # Write backup file
        with open(backup_path, "w", encoding="utf-8") as backup_file:
            json.dump(
                backup_data,
                backup_file,
                indent=2,
                ensure_ascii=False
            )

        backup_size_bytes = os.path.getsize(backup_path)

        if backup_size_bytes < 1024:
            backup_size = f"{backup_size_bytes} B"
        elif backup_size_bytes < 1024 * 1024:
            backup_size = f"{backup_size_bytes / 1024:.2f} KB"
        else:
            backup_size = f"{backup_size_bytes / (1024 * 1024):.2f} MB"

        # Save backup history
        cursor.execute('''
            INSERT INTO "BackupHistory"
            (
                backup_name,
                backup_type,
                backup_size,
                created_by,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING backup_id, backup_date
        ''', (
            backup_name,
            "Full",
            backup_size,
            created_by,
            "Success"
        ))

        backup_record = cursor.fetchone()

        conn.commit()

        return jsonify({
            "message": "Backup created successfully",
            "backup_id": backup_record[0],
            "backup_name": backup_name,
            "backup_type": "Full",
            "backup_size": backup_size,
            "created_by": created_by,
            "status": "Success",
            "file_path": backup_path
        }), 201

    except Exception as error:
        conn.rollback()

        return jsonify({
            "error": "Backup creation failed",
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        conn.close()