import logging
import math
from datetime import datetime
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


def get_all_audit_logs(limit=50, page=1, search=None, action=None, table_name=None, start_date=None, end_date=None):
    """
    Retrieves filtered and paginated audit logs for the owner audit logs API endpoint.
    Supports search, action, table_name, start_date, end_date, and deterministic pagination.
    """
    # 1. Validate page
    try:
        parsed_page = int(page)
        if parsed_page < 1:
            return None, "Invalid page: must be a positive integer"
    except (ValueError, TypeError):
        return None, "Invalid page: must be a positive integer"

    # 2. Validate limit (default 50, maximum 100)
    try:
        parsed_limit = int(limit)
        if parsed_limit < 1 or parsed_limit > 100:
            return None, "Invalid limit: must be an integer between 1 and 100"
    except (ValueError, TypeError):
        return None, "Invalid limit: must be an integer between 1 and 100"

    # 3. Validate start_date and end_date formats
    clean_start_date = None
    if start_date is not None and str(start_date).strip():
        try:
            datetime.strptime(str(start_date).strip(), "%Y-%m-%d")
            clean_start_date = str(start_date).strip()
        except ValueError:
            return None, "Invalid start_date format. Expected YYYY-MM-DD"

    clean_end_date = None
    if end_date is not None and str(end_date).strip():
        try:
            datetime.strptime(str(end_date).strip(), "%Y-%m-%d")
            clean_end_date = str(end_date).strip()
        except ValueError:
            return None, "Invalid end_date format. Expected YYYY-MM-DD"

    if clean_start_date and clean_end_date and clean_start_date > clean_end_date:
        return None, "Start date cannot be after end date"

    # 4. Clean filter strings
    clean_action = str(action).strip().upper() if (action and str(action).strip() and str(action).strip().lower() != "all") else None
    clean_table = str(table_name).strip() if (table_name and str(table_name).strip() and str(table_name).strip().lower() != "all") else None
    clean_search = str(search).strip() if (search and str(search).strip()) else None

    # 5. Build parameterized query clauses
    where_clauses = []
    params = []

    if clean_start_date:
        where_clauses.append('al.action_time >= %s')
        params.append(f"{clean_start_date} 00:00:00")

    if clean_end_date:
        # Inclusive end date through end of the selected calendar day
        where_clauses.append('al.action_time <= %s')
        params.append(f"{clean_end_date} 23:59:59.999999")

    if clean_action:
        where_clauses.append('UPPER(al.action) = %s')
        params.append(clean_action)

    if clean_table:
        where_clauses.append('LOWER(al.table_name) = LOWER(%s)')
        params.append(clean_table)

    if clean_search:
        search_pattern = f"%{clean_search}%"
        where_clauses.append("""(
            u.username ILIKE %s
            OR al.action ILIKE %s
            OR al.table_name ILIKE %s
            OR CAST(al.record_id AS TEXT) ILIKE %s
        )""")
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 6. Execute Count Query for total matching records
        count_query = f'''
            SELECT COUNT(*)
            FROM public."AuditLogs" al
            LEFT JOIN public."Users" u ON al.user_id = u.user_id
            LEFT JOIN public."Roles" r ON u.role_id = r.role_id
            {where_sql}
        '''
        cursor.execute(count_query, tuple(params))
        count_row = cursor.fetchone()
        total_count = count_row[0] if count_row else 0

        # 7. Compute total pages
        total_pages = math.ceil(total_count / parsed_limit) if total_count > 0 else 0

        # 8. Execute Data Query with pagination and role join
        offset = (parsed_page - 1) * parsed_limit
        data_query = f'''
            SELECT
                al.log_id,
                al.user_id,
                al.action,
                al.table_name,
                al.record_id,
                al.action_time,
                al.ip_address,
                COALESCE(u.username, CASE WHEN al.user_id IS NOT NULL THEN CONCAT('User #', al.user_id::text) ELSE 'System' END) AS username,
                COALESCE(r.role_name, 'Unknown') AS role_name
            FROM public."AuditLogs" al
            LEFT JOIN public."Users" u ON al.user_id = u.user_id
            LEFT JOIN public."Roles" r ON u.role_id = r.role_id
            {where_sql}
            ORDER BY al.action_time DESC, al.log_id DESC
            LIMIT %s OFFSET %s
        '''
        query_params = list(params) + [parsed_limit, offset]
        cursor.execute(data_query, tuple(query_params))
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
                "username": row[7],
                "role_name": row[8]
            })

        result = {
            "logs": audit_logs,
            "total": total_count,
            "page": parsed_page,
            "limit": parsed_limit,
            "total_pages": total_pages
        }
        return result, None
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

