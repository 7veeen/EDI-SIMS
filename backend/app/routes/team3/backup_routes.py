import json
import logging
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file

from app.services.team3 import backup_service as backups
from app.utils.jwt_utils import role_required, token_required

backup_bp = Blueprint("backup", __name__)
logger = logging.getLogger(__name__)


def _server_error(message):
    logger.exception(message)
    return jsonify({"error": message}), 500


@backup_bp.route("/api/backups", methods=["POST"])
@token_required
def create_backup_route():
    try:
        metadata = backups.create_backup(created_by=request.user_id)
        return jsonify({"message": "Backup created successfully", "backup": metadata}), 201
    except Exception:
        return _server_error("Unable to create backup")


@backup_bp.route("/api/backups", methods=["GET"])
@token_required
def get_backups():
    try:
        return jsonify({"backups": backups.list_backups()}), 200
    except Exception:
        return _server_error("Unable to retrieve backup history")


@backup_bp.route("/api/backups/<int:backup_id>", methods=["GET"])
@token_required
def get_single_backup(backup_id):
    try:
        return jsonify({"backup": backups.get_backup(backup_id)}), 200
    except backups.BackupNotFound:
        return jsonify({"error": "Backup not found"}), 404
    except Exception:
        return _server_error("Unable to retrieve backup")


@backup_bp.route("/api/backups/<int:backup_id>/download", methods=["GET"])
@token_required
def download_backup(backup_id):
    try:
        metadata, file_data = backups.download_backup(backup_id)
        return send_file(BytesIO(file_data), mimetype="application/json", as_attachment=True,
                         download_name=metadata["backup_name"])
    except backups.BackupNotFound:
        return jsonify({"error": "Backup not found"}), 404
    except backups.BackupStorageNotFound:
        return jsonify({"error": "Backup file is missing from storage"}), 404
    except Exception:
        return _server_error("Unable to download backup")


@backup_bp.route("/api/backups/<int:backup_id>/restore", methods=["POST"])
@role_required("Owner", "Manager")
def restore_backup(backup_id):
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict) or ("dry_run" in data and not isinstance(data["dry_run"], bool)):
        return jsonify({"error": "Request must be a JSON object with a boolean dry_run"}), 400
    dry_run = data.get("dry_run", True)
    try:
        _, file_data = backups.download_backup(backup_id)
    except backups.BackupNotFound:
        return jsonify({"error": "Backup not found"}), 404
    except backups.BackupStorageNotFound:
        return jsonify({"error": "Backup file is missing from storage"}), 404
    except Exception:
        return _server_error("Unable to retrieve backup for restore")

    try:
        backup_data = json.loads(file_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({"error": "Backup file is not valid JSON"}), 400
    validation = backups.validate_backup(backup_data)
    if not validation["valid"]:
        return jsonify({"error": "Backup validation failed", "details": validation}), 400
    if dry_run:
        return jsonify(backups.prepare_restore(backup_data)), 200
    result = backups.restore_backup(backup_data)
    if not result["valid"]:
        return jsonify(result), 500
    return jsonify(result), 200


@backup_bp.route("/api/backups/<int:backup_id>", methods=["DELETE"])
@role_required("Owner", "Manager")
def delete_backup(backup_id):
    try:
        backups.delete_backup(backup_id)
        return jsonify({"message": "Backup deleted successfully"}), 200
    except backups.BackupNotFound:
        return jsonify({"error": "Backup not found"}), 404
    except Exception:
        return _server_error("Unable to delete backup")
