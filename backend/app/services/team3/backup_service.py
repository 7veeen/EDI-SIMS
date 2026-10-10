import json
import logging
from datetime import datetime, timezone

from app.config.supabase_client import supabase

logger = logging.getLogger(__name__)
BUCKET = "backups"
BACKUP_TABLES = [
    "Roles", "Users", "Categories", "Products", "Suppliers",
    "SupplierQuotations", "PurchaseOrders", "PurchaseOrderItems", "Inventory",
    "StockTransactions", "Notifications", "AuditLogs", "SystemStatus", "Reports",
]
RESTORE_TABLES = [
    ("Roles", "role_id"), ("Users", "user_id"), ("Categories", "category_id"),
    ("Products", "product_id"), ("Suppliers", "supplier_id"),
    ("SupplierQuotations", "quotation_id"), ("PurchaseOrders", "purchase_order_id"),
    ("PurchaseOrderItems", "purchase_order_item_id"), ("Inventory", "inventory_id"),
    ("StockTransactions", "transaction_id"), ("Notifications", "notification_id"),
    ("AuditLogs", "log_id"), ("SystemStatus", "status_id"), ("Reports", "report_id"),
]
HISTORY_FIELDS = "backup_id, backup_name, backup_type, backup_date, backup_size, created_by, status"
BACKUP_PAGE_SIZE = 500


class BackupNotFound(Exception):
    pass


class BackupStorageNotFound(Exception):
    pass


def create_backup(created_by):
    if created_by is None:
        raise ValueError("Authenticated user ID is required")
    payload = {table: _read_all_rows(table) for table in BACKUP_TABLES}
    created_at = datetime.now(timezone.utc)
    payload = {"backup_info": {"backup_type": "full", "created_at": created_at.isoformat(), "version": "1.0"}, **payload}
    file_data = json.dumps(payload, indent=2, default=str).encode("utf-8")
    backup_name = f"backup_{created_at.strftime('%Y%m%d_%H%M%S_%f')}.json"
    storage = supabase.storage.from_(BUCKET)
    storage.upload(backup_name, file_data, {"content-type": "application/json"})
    try:
        response = supabase.table("BackupHistory").insert({
            "backup_name": backup_name, "backup_type": "Full",
            "backup_date": created_at.isoformat(), "backup_size": len(file_data),
            "created_by": created_by, "status": "Success",
        }).execute()
    except Exception:
        logger.exception("Could not write backup history; removing orphaned storage object")
        try:
            storage.remove([backup_name])
        except Exception:
            logger.exception("Could not clean up orphaned backup object %s", backup_name)
        raise
    return response.data[0] if response.data else {
        "backup_name": backup_name, "backup_type": "Full", "backup_date": created_at.isoformat(),
        "backup_size": len(file_data), "created_by": created_by, "status": "Success",
    }


def _read_all_rows(table_name):
    """Read every row in bounded pages to avoid PostgREST response limits."""
    records = []
    offset = 0
    while True:
        page = (supabase.table(table_name).select("*")
                .range(offset, offset + BACKUP_PAGE_SIZE - 1).execute().data or [])
        records.extend(page)
        if len(page) < BACKUP_PAGE_SIZE:
            return records
        offset += BACKUP_PAGE_SIZE


def list_backups():
    return (supabase.table("BackupHistory").select(HISTORY_FIELDS)
            .order("backup_date", desc=True).execute().data or [])


def get_backup(backup_id):
    response = (supabase.table("BackupHistory").select(HISTORY_FIELDS)
                .eq("backup_id", backup_id).maybe_single().execute())
    if not response.data:
        raise BackupNotFound()
    return response.data


def download_backup(backup_id):
    metadata = get_backup(backup_id)
    try:
        return metadata, supabase.storage.from_(BUCKET).download(metadata["backup_name"])
    except Exception as exc:
        if _is_missing_storage_object(exc):
            raise BackupStorageNotFound() from exc
        raise


def delete_backup(backup_id):
    metadata = get_backup(backup_id)
    try:
        supabase.storage.from_(BUCKET).remove([metadata["backup_name"]])
    except Exception as exc:
        if not _is_missing_storage_object(exc):
            raise
    supabase.table("BackupHistory").delete().eq("backup_id", backup_id).execute()
    return metadata


def _is_missing_storage_object(exc):
    status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
    message = str(exc).lower()
    return status == 404 or "not found" in message or "object not found" in message


def validate_backup(backup_data):
    if not isinstance(backup_data, dict):
        return {"valid": False, "message": "Backup must be a JSON object"}
    info = backup_data.get("backup_info")
    if not isinstance(info, dict) or info.get("backup_type") != "full":
        return {"valid": False, "message": "Backup information is missing or invalid"}
    missing = [table for table in BACKUP_TABLES if table not in backup_data]
    if missing:
        return {"valid": False, "message": "Backup is missing required tables", "missing_tables": missing}
    for table, primary_key in RESTORE_TABLES:
        records = backup_data[table]
        if not isinstance(records, list):
            return {"valid": False, "message": "Table data must be a list", "invalid_table": table}
        keys = set()
        for record in records:
            if not isinstance(record, dict) or primary_key not in record or record[primary_key] is None:
                return {"valid": False, "message": "A record is invalid or missing its primary key", "invalid_table": table}
            if record[primary_key] in keys:
                return {"valid": False, "message": "Duplicate primary key in backup", "invalid_table": table}
            keys.add(record[primary_key])
    return {"valid": True, "message": "Backup structure is valid"}


def prepare_restore(backup_data):
    validation = validate_backup(backup_data)
    if not validation["valid"]:
        return validation
    return {"valid": True, "message": "Restore plan prepared successfully", "dry_run": True,
            "restore_order": [{"table": table, "primary_key": pk, "records": len(backup_data[table])}
                              for table, pk in RESTORE_TABLES]}


def restore_backup(backup_data):
    validation = validate_backup(backup_data)
    if not validation["valid"]:
        return validation
    try:
        response = supabase.rpc("restore_application_backup", {"p_backup": backup_data}).execute()
        restored = response.data
        if isinstance(restored, str):
            restored = json.loads(restored)
        return {"valid": True, "message": "Backup restored successfully", "results": restored}
    except Exception:
        logger.exception("Transactional application backup restore failed")
        return {"valid": False, "message": "Restore failed; no changes were committed"}
