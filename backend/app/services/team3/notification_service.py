from datetime import datetime
from app.extensions import get_db_connection


def get_user_notifications(user_id, is_read=None, limit=None, offset=None):
    """
    Retrieve notifications strictly scoped to the authenticated user.
    Enforces complete user isolation: never returns notifications belonging to another user.
    """
    if not user_id:
        return None, "user_id is required", 400

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid user_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                notification_id,
                user_id,
                title,
                message,
                notification_type,
                is_read,
                created_at,
                read_at,
                reference_type,
                reference_id,
                priority
            FROM "Notifications"
            WHERE user_id = %s
        """
        params = [uid]

        if is_read is not None:
            query += " AND is_read = %s"
            params.append(bool(is_read))

        query += " ORDER BY notification_id DESC"

        if limit is not None:
            try:
                query += " LIMIT %s"
                params.append(int(limit))
            except (ValueError, TypeError):
                pass

        if offset is not None:
            try:
                query += " OFFSET %s"
                params.append(int(offset))
            except (ValueError, TypeError):
                pass

        cursor.execute(query, tuple(params))
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
                "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
                "read_at": row[7].isoformat() if row[7] and hasattr(row[7], "isoformat") else (str(row[7]) if row[7] else None),
                "reference_type": row[8],
                "reference_id": row[9],
                "priority": row[10] or "Normal"
            })

        return notifications, None, 200

    except Exception as e:
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_notification_by_id(notification_id, user_id):
    """
    Retrieve a single notification by ID.
    Enforces strict ownership check (IDOR prevention):
    Returns 404 if not found, 403 if notification belongs to another user.
    """
    if not notification_id:
        return None, "notification_id is required", 400
    if not user_id:
        return None, "user_id is required", 400

    try:
        nid = int(notification_id)
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid ID parameters", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                notification_id,
                user_id,
                title,
                message,
                notification_type,
                is_read,
                created_at,
                read_at,
                reference_type,
                reference_id,
                priority
            FROM "Notifications"
            WHERE notification_id = %s
        """, (nid,))
        row = cursor.fetchone()

        if not row:
            return None, "Notification not found", 404

        owner_id = row[1]
        if owner_id != uid:
            return None, "Access denied. You do not have permission to view this notification.", 403

        data = {
            "notification_id": row[0],
            "user_id": row[1],
            "title": row[2],
            "message": row[3],
            "notification_type": row[4],
            "is_read": row[5],
            "created_at": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6]),
            "read_at": row[7].isoformat() if row[7] and hasattr(row[7], "isoformat") else (str(row[7]) if row[7] else None),
            "reference_type": row[8],
            "reference_id": row[9],
            "priority": row[10] or "Normal"
        }

        return data, None, 200

    except Exception as e:
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_unread_count(user_id):
    """
    Retrieve the count of unread notifications for the authenticated user only.
    """
    if not user_id:
        return None, "user_id is required", 400

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid user_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*)
            FROM "Notifications"
            WHERE user_id = %s AND is_read = FALSE
        """, (uid,))
        count = cursor.fetchone()[0]

        return {"success": True, "unread_count": int(count or 0)}, None, 200

    except Exception as e:
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def mark_notification_as_read(notification_id, user_id):
    """
    Mark a single notification as read.
    Enforces strict ownership check (IDOR prevention):
    Returns 404 if not found, 403 if belongs to another user.
    Updates is_read = TRUE and read_at = CURRENT_TIMESTAMP idempotently.
    """
    if not notification_id:
        return None, "notification_id is required", 400
    if not user_id:
        return None, "user_id is required", 400

    try:
        nid = int(notification_id)
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid ID parameters", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT notification_id, user_id, is_read, read_at
            FROM "Notifications"
            WHERE notification_id = %s
        """, (nid,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Notification not found", 404

        owner_id = row[1]
        if owner_id != uid:
            conn.rollback()
            return None, "Access denied. You do not have permission to modify this notification.", 403

        is_already_read = row[2]
        existing_read_at = row[3]

        if is_already_read:
            conn.commit()
            return {
                "notification_id": nid,
                "is_read": True,
                "read_at": existing_read_at.isoformat() if existing_read_at and hasattr(existing_read_at, "isoformat") else (str(existing_read_at) if existing_read_at else None),
                "message": "Notification is already marked as read"
            }, None, 200

        cursor.execute("""
            UPDATE "Notifications"
            SET is_read = TRUE,
                read_at = CURRENT_TIMESTAMP
            WHERE notification_id = %s AND user_id = %s
            RETURNING notification_id, is_read, read_at
        """, (nid, uid))
        updated_row = cursor.fetchone()
        conn.commit()

        updated_read_at = updated_row[2]
        return {
            "notification_id": updated_row[0],
            "is_read": updated_row[1],
            "read_at": updated_read_at.isoformat() if updated_read_at and hasattr(updated_read_at, "isoformat") else (str(updated_read_at) if updated_read_at else None)
        }, None, 200

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def mark_all_as_read(user_id):
    """
    Mark all unread notifications belonging to the authenticated user as read.
    Sets is_read = TRUE and read_at = CURRENT_TIMESTAMP.
    Never modifies notifications belonging to another user.
    """
    if not user_id:
        return None, "user_id is required", 400

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid user_id", 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE "Notifications"
            SET is_read = TRUE,
                read_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND is_read = FALSE
            RETURNING notification_id
        """, (uid,))
        updated_rows = cursor.fetchall()
        updated_count = len(updated_rows)

        conn.commit()

        return {
            "success": True,
            "message": "All notifications marked as read",
            "updated_count": updated_count
        }, None, 200

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_notification(
    user_id,
    title,
    message,
    notification_type="Info",
    priority="Normal",
    reference_type=None,
    reference_id=None,
    conn=None
):
    """
    Create a new notification for a specific user.
    Includes application-level duplicate prevention:
    If an unread notification already exists for the same user with the same
    reference (reference_type + reference_id + notification_type), or same title + type,
    skips insertion to prevent redundant alert spam.
    """
    if not user_id:
        return None, "user_id is required", 400
    if not title or not title.strip():
        return None, "title is required", 400
    if not message or not message.strip():
        return None, "message is required", 400

    try:
        uid = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid user_id", 400

    ref_id = None
    if reference_id is not None and reference_id != "":
        try:
            ref_id = int(reference_id)
        except (ValueError, TypeError):
            ref_id = None

    ref_type = reference_type.strip() if reference_type else None
    notif_type = notification_type.strip() if notification_type else "Info"
    prio = priority.strip() if priority else "Normal"
    clean_title = title.strip()
    clean_message = message.strip()

    should_close_conn = False
    cursor = None
    try:
        if conn is None:
            conn = get_db_connection()
            conn.autocommit = False
            should_close_conn = True

        cursor = conn.cursor()

        # Inactive user check: never send notification to inactive or non-existent user
        cursor.execute('SELECT user_id, status FROM "Users" WHERE user_id = %s', (uid,))
        user_row = cursor.fetchone()
        if not user_row or user_row[1] != 'Active':
            if should_close_conn:
                conn.rollback()
            return {
                "created": False,
                "skipped": True,
                "reason": "User is inactive or not found"
            }, None, 200

        # Duplicate Prevention Check:
        # Check if an identical unread notification is already pending for this user and event/reference
        if ref_type and ref_id is not None:
            cursor.execute("""
                SELECT notification_id
                FROM "Notifications"
                WHERE user_id = %s
                  AND is_read = FALSE
                  AND reference_type = %s
                  AND reference_id = %s
                  AND notification_type = %s
                LIMIT 1
            """, (uid, ref_type, ref_id, notif_type))
        else:
            cursor.execute("""
                SELECT notification_id
                FROM "Notifications"
                WHERE user_id = %s
                  AND is_read = FALSE
                  AND title = %s
                  AND notification_type = %s
                LIMIT 1
            """, (uid, clean_title, notif_type))

        duplicate = cursor.fetchone()
        if duplicate:
            if should_close_conn:
                conn.commit()
            return {
                "notification_id": duplicate[0],
                "created": False,
                "skipped": True,
                "reason": "Equivalent unread notification already exists"
            }, None, 200

        # Insert new notification
        cursor.execute("""
            INSERT INTO "Notifications" (
                user_id,
                title,
                message,
                notification_type,
                is_read,
                created_at,
                reference_type,
                reference_id,
                priority
            )
            VALUES (%s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP, %s, %s, %s)
            RETURNING notification_id, created_at
        """, (
            uid,
            clean_title,
            clean_message,
            notif_type,
            ref_type,
            ref_id,
            prio
        ))
        row = cursor.fetchone()
        new_id = row[0]
        created_at = row[1]

        if should_close_conn:
            conn.commit()

        return {
            "notification_id": new_id,
            "user_id": uid,
            "title": clean_title,
            "message": clean_message,
            "notification_type": notif_type,
            "is_read": False,
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
            "reference_type": ref_type,
            "reference_id": ref_id,
            "priority": prio,
            "created": True
        }, None, 201

    except Exception as e:
        if should_close_conn and conn:
            conn.rollback()
        return None, f"Database error: {str(e)}", 500
    finally:
        if cursor:
            cursor.close()
        if should_close_conn and conn:
            conn.close()


def get_active_managers_and_owners(exclude_user_id=None):
    """
    Return list of user_ids for active Managers and Owners.
    Optionally exclude a user (e.g. the actor who performed the action).
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT u.user_id
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE r.role_name IN ('Owner', 'Manager')
              AND u.status = 'Active'
        """
        params = []
        if exclude_user_id is not None:
            try:
                query += " AND u.user_id != %s"
                params.append(int(exclude_user_id))
            except (ValueError, TypeError):
                pass
        cursor.execute(query, tuple(params))
        return [r[0] for r in cursor.fetchall()]
    except Exception:
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_supplier_user_id(supplier_id):
    """
    Return the active user_id associated with a supplier profile.
    """
    if not supplier_id:
        return None
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id
            FROM "Suppliers" s
            JOIN "Users" u ON s.user_id = u.user_id
            WHERE s.supplier_id = %s AND u.status = 'Active'
        """, (int(supplier_id),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_po_creator_user_id(po_id):
    """
    Return the active user_id of the creator (ordered_by) of a purchase order.
    """
    if not po_id:
        return None
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id
            FROM "PurchaseOrders" po
            JOIN "Users" u ON po.ordered_by = u.user_id
            WHERE po.purchase_order_id = %s AND u.status = 'Active'
        """, (int(po_id),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_assigned_employee_user_id(shipment_id):
    """
    Return the active user_id of the employee assigned to a shipment.
    """
    if not shipment_id:
        return None
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id
            FROM "Shipments" s
            JOIN "Users" u ON s.assigned_employee_id = u.user_id
            WHERE s.shipment_id = %s AND u.status = 'Active'
        """, (int(shipment_id),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
