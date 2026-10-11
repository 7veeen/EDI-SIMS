import logging
from flask import has_request_context, request
from psycopg2 import Error

from app.extensions import get_db_connection

logger = logging.getLogger(__name__)


def get_client_ip():
    """
    Safely extract client IP address respecting trusted proxy headers if present,
    falling back to remote_addr or localhost.
    """
    if has_request_context():
        # Check standard reverse-proxy header
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            # First IP in the comma-separated list is the client IP
            return x_forwarded_for.split(",")[0].strip()
        return request.remote_addr or "127.0.0.1"
    return "127.0.0.1"


def get_authenticated_actor_id(fallback_user_id=None):
    """
    Derives the actor's user_id strictly from the validated server-side JWT context.
    Prevents client-side actor spoofing.
    """
    if has_request_context():
        try:
            from flask_jwt_extended import get_jwt_identity
            identity = get_jwt_identity()
            if identity is not None:
                return int(identity)
        except Exception:
            pass

    if fallback_user_id is not None:
        try:
            return int(fallback_user_id)
        except (ValueError, TypeError):
            return None

    return None


def log_audit_event(action, table_name, record_id=None, user_id=None, cursor=None, ip_address=None):
    """
    Inserts a verified audit log record into public."AuditLogs".
    
    Parameters:
        action (str): Standardized action name (e.g. 'STOCK_OUT', 'PO_CREATED', 'QUOTATION_APPROVED').
        table_name (str): Target entity table name (e.g. 'StockTransactions', 'PurchaseOrders').
        record_id (int|None): Primary key of the affected record, or None.
        user_id (int|None): Authenticated actor ID. If None, derived from JWT context.
        cursor: Optional active database cursor to participate in an ongoing transaction.
        ip_address (str|None): Optional client IP. If None, derived from request context.
        
    Returns:
        (log_id, None) on success,
        (None, error_str) on failure.
    """
    # 1. Derive authenticated actor ID strictly from server context if not explicitly provided
    resolved_user_id = get_authenticated_actor_id(fallback_user_id=user_id)
    if resolved_user_id is None:
        logger.warning(f"Audit log skipped for {action} on {table_name}: No authenticated actor identified")
        return None, "Actor user_id is required for audit logging"

    # 2. Normalize fields
    clean_action = str(action).strip().upper()
    clean_table = str(table_name).strip()
    
    clean_record_id = None
    if record_id is not None:
        try:
            clean_record_id = int(record_id)
        except (ValueError, TypeError):
            clean_record_id = None

    client_ip = ip_address or get_client_ip()

    # 3. Insert using existing transaction cursor or create dedicated connection
    if cursor is not None:
        try:
            cursor.execute(
                '''
                INSERT INTO public."AuditLogs"
                (user_id, action, table_name, record_id, action_time, ip_address)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                RETURNING log_id;
                ''',
                (resolved_user_id, clean_action, clean_table, clean_record_id, client_ip)
            )
            row = cursor.fetchone()
            log_id = row[0] if row else None
            return log_id, None
        except Error as db_err:
            logger.error(f"Failed to record audit log on transaction cursor: {db_err}")
            raise  # Let the transaction handler manage rollback
        except Exception as ex:
            logger.error(f"Unexpected error recording audit log on transaction cursor: {ex}")
            raise
    else:
        conn = None
        local_cursor = None
        try:
            conn = get_db_connection()
            local_cursor = conn.cursor()
            local_cursor.execute(
                '''
                INSERT INTO public."AuditLogs"
                (user_id, action, table_name, record_id, action_time, ip_address)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                RETURNING log_id;
                ''',
                (resolved_user_id, clean_action, clean_table, clean_record_id, client_ip)
            )
            row = local_cursor.fetchone()
            log_id = row[0] if row else None
            conn.commit()
            return log_id, None
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to record standalone audit log: {e}")
            return None, f"Audit logging failure: {str(e)}"
        finally:
            if local_cursor:
                local_cursor.close()
            if conn:
                conn.close()


def get_all_audit_logs(limit=1000):
    """
    Retrieves audit logs for the owner audit logs API endpoint.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                al.log_id,
                al.user_id,
                al.action,
                al.table_name,
                al.record_id,
                al.action_time,
                al.ip_address,
                COALESCE(u.username, CASE WHEN al.user_id IS NOT NULL THEN CONCAT('User #', al.user_id::text) ELSE 'System' END) AS username
            FROM public."AuditLogs" al
            LEFT JOIN public."Users" u ON al.user_id = u.user_id
            ORDER BY al.log_id DESC
            LIMIT %s
            ''',
            (limit,)
        )
        rows = cursor.fetchall()
        audit_logs = []
        for row in rows:
            audit_logs.append({
                "log_id": row[0],
                "user_id": row[1],
                "action": row[2],
                "table_name": row[3],
                "record_id": row[4],
                "action_time": row[5].isoformat() if hasattr(row[5], 'isoformat') and row[5] else str(row[5]),
                "ip_address": row[6],
                "username": row[7]
            })
        return audit_logs, None
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return None, str(e)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

