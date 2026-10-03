import re
from app.extensions import get_db_connection


def validate_email(email):
    if not email:
        return True
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def get_suppliers(search=None, status=None):
    """
    Retrieve suppliers with optional search and status filtering,
    including linked username, order counts, and quotation counts.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.phone,
                s.email,
                s.status,
                s.user_id,
                u.username,
                COUNT(DISTINCT po.purchase_order_id) AS total_orders,
                COUNT(DISTINCT sq.quotation_id) AS total_quotations
            FROM "Suppliers" s
            LEFT JOIN "Users" u ON s.user_id = u.user_id
            LEFT JOIN "PurchaseOrders" po ON s.supplier_id = po.supplier_id
            LEFT JOIN "SupplierQuotations" sq ON s.supplier_id = sq.supplier_id
            WHERE 1=1
        """
        params = []

        if search and search.strip():
            search_param = f"%{search.strip()}%"
            query += """
                AND (
                    s.supplier_name ILIKE %s
                    OR s.contact_person ILIKE %s
                    OR s.email ILIKE %s
                    OR s.phone ILIKE %s
                    OR u.username ILIKE %s
                )
            """
            params.extend([search_param, search_param, search_param, search_param, search_param])

        if status and status.strip():
            query += " AND s.status = %s"
            params.append(status.strip())

        query += """
            GROUP BY s.supplier_id, s.supplier_name, s.contact_person, s.phone, s.email, s.status, s.user_id, u.username
            ORDER BY s.supplier_id ASC
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        suppliers = []
        for r in rows:
            suppliers.append({
                "supplier_id": r[0],
                "supplier_name": r[1],
                "contact_person": r[2] or "",
                "phone": r[3] or "",
                "email": r[4] or "",
                "status": r[5],
                "user_id": r[6],
                "username": r[7] or "",
                "total_orders": r[8],
                "total_quotations": r[9]
            })

        return suppliers, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_supplier_by_id(supplier_id):
    """
    Retrieve single supplier details along with recent orders and quotations.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                s.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.phone,
                s.email,
                s.status,
                s.user_id,
                u.username,
                COUNT(DISTINCT po.purchase_order_id) AS total_orders,
                COUNT(DISTINCT sq.quotation_id) AS total_quotations
            FROM "Suppliers" s
            LEFT JOIN "Users" u ON s.user_id = u.user_id
            LEFT JOIN "PurchaseOrders" po ON s.supplier_id = po.supplier_id
            LEFT JOIN "SupplierQuotations" sq ON s.supplier_id = sq.supplier_id
            WHERE s.supplier_id = %s
            GROUP BY s.supplier_id, s.supplier_name, s.contact_person, s.phone, s.email, s.status, s.user_id, u.username
        """
        cursor.execute(query, (supplier_id,))
        r = cursor.fetchone()

        if not r:
            return None, "Supplier not found"

        # Fetch recent purchase orders
        cursor.execute("""
            SELECT purchase_order_id, total_amount, status, order_date, expected_delivery
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
            ORDER BY purchase_order_id DESC
            LIMIT 5
        """, (supplier_id,))
        po_rows = cursor.fetchall()
        recent_orders = []
        for po in po_rows:
            recent_orders.append({
                "purchase_order_id": po[0],
                "total_amount": float(po[1]) if po[1] is not None else 0.0,
                "status": po[2],
                "order_date": po[3].isoformat() if po[3] else None,
                "expected_delivery": po[4].isoformat() if po[4] else None
            })

        # Fetch recent quotations
        cursor.execute("""
            SELECT sq.quotation_id, sq.product_id, p.product_name, sq.quoted_price, sq.quantity, sq.status, sq.valid_until
            FROM "SupplierQuotations" sq
            LEFT JOIN "Products" p ON sq.product_id = p.product_id
            WHERE sq.supplier_id = %s
            ORDER BY sq.quotation_id DESC
            LIMIT 5
        """, (supplier_id,))
        sq_rows = cursor.fetchall()
        recent_quotations = []
        for sq in sq_rows:
            recent_quotations.append({
                "quotation_id": sq[0],
                "product_id": sq[1],
                "product_name": sq[2] or f"Product #{sq[1]}",
                "quoted_price": float(sq[3]) if sq[3] is not None else 0.0,
                "quantity": sq[4],
                "status": sq[5],
                "valid_until": sq[6].isoformat() if sq[6] else None
            })

        supplier = {
            "supplier_id": r[0],
            "supplier_name": r[1],
            "contact_person": r[2] or "",
            "phone": r[3] or "",
            "email": r[4] or "",
            "status": r[5],
            "user_id": r[6],
            "username": r[7] or "",
            "total_orders": r[8],
            "total_quotations": r[9],
            "recent_orders": recent_orders,
            "recent_quotations": recent_quotations
        }

        return supplier, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_supplier_by_user_id(user_id):
    """
    Find the supplier linked to an authenticated user_id.
    Used for Phase 7 (Supplier-specific access / login mapping).
    """
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None, "Invalid user_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT supplier_id
            FROM "Suppliers"
            WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()

        if not row:
            return None, "No supplier profile linked to this user account"

        supplier_id = row[0]
        return get_supplier_by_id(supplier_id)

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_available_supplier_users(current_supplier_id=None):
    """
    Get users with role 'Supplier' who are either unlinked,
    or currently linked to current_supplier_id.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT u.user_id, u.username, u.email, u.status, s.supplier_id, s.supplier_name
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            LEFT JOIN "Suppliers" s ON u.user_id = s.user_id
            WHERE r.role_name = 'Supplier' AND u.status = 'Active'
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        users = []
        for r in rows:
            linked_supplier_id = r[4]
            # Include if not linked to any supplier, or linked to current_supplier_id
            if linked_supplier_id is None or (current_supplier_id and linked_supplier_id == current_supplier_id):
                users.append({
                    "user_id": r[0],
                    "username": r[1],
                    "email": r[2] or "",
                    "is_assigned": linked_supplier_id is not None
                })

        return users, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_supplier(data):
    """
    Create a new supplier.
    Validates required fields, unique name, email format, and user_id relation.
    """
    if not data or not isinstance(data, dict):
        return None, "Request body is required"

    supplier_name = data.get("supplier_name")
    if not supplier_name or not str(supplier_name).strip():
        return None, "Supplier name is required"

    supplier_name = str(supplier_name).strip()
    contact_person = str(data.get("contact_person", "")).strip() or None
    phone = str(data.get("phone", "")).strip() or None
    email = str(data.get("email", "")).strip() or None
    status = str(data.get("status", "Active")).strip()
    user_id = data.get("user_id")

    if status not in ["Active", "Inactive"]:
        return None, "Status must be either 'Active' or 'Inactive'"

    if email and not validate_email(email):
        return None, "Invalid email address format"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check unique supplier_name
        cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE LOWER(supplier_name) = LOWER(%s)', (supplier_name,))
        if cursor.fetchone():
            return None, "Supplier with this name already exists"

        # Validate user_id if provided
        if user_id is not None and str(user_id).strip() != "":
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return None, "Invalid user_id"

            # Check if user exists and has Supplier role
            cursor.execute("""
                SELECT u.user_id, r.role_name
                FROM "Users" u
                JOIN "Roles" r ON u.role_id = r.role_id
                WHERE u.user_id = %s
            """, (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return None, "Selected user does not exist"
            if user_row[1] != "Supplier":
                return None, "Selected user does not have the 'Supplier' role"

            # Check if user is already linked to another supplier
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (user_id,))
            existing_link = cursor.fetchone()
            if existing_link:
                return None, f"User is already linked to supplier #{existing_link[0]}"
        else:
            user_id = None

        # Insert new supplier
        cursor.execute("""
            INSERT INTO "Suppliers" (supplier_name, contact_person, phone, email, status, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING supplier_id, supplier_name, contact_person, phone, email, status, user_id
        """, (supplier_name, contact_person, phone, email, status, user_id))

        new_row = cursor.fetchone()
        conn.commit()

        created_supplier = {
            "supplier_id": new_row[0],
            "supplier_name": new_row[1],
            "contact_person": new_row[2] or "",
            "phone": new_row[3] or "",
            "email": new_row[4] or "",
            "status": new_row[5],
            "user_id": new_row[6]
        }

        return created_supplier, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_supplier(supplier_id, data):
    """
    Update supplier information.
    """
    if not data or not isinstance(data, dict):
        return None, "Request body is required"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existence
        cursor.execute('SELECT supplier_id, supplier_name, status, user_id FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
        existing = cursor.fetchone()
        if not existing:
            return None, "Supplier not found"

        supplier_name = data.get("supplier_name")
        contact_person = data.get("contact_person")
        phone = data.get("phone")
        email = data.get("email")
        status = data.get("status")
        user_id = data.get("user_id")

        updates = []
        params = []

        if supplier_name is not None:
            name_str = str(supplier_name).strip()
            if not name_str:
                return None, "Supplier name cannot be empty"
            # Check unique name
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE LOWER(supplier_name) = LOWER(%s) AND supplier_id != %s', (name_str, supplier_id))
            if cursor.fetchone():
                return None, "Supplier with this name already exists"
            updates.append("supplier_name = %s")
            params.append(name_str)

        if contact_person is not None:
            updates.append("contact_person = %s")
            params.append(str(contact_person).strip() or None)

        if phone is not None:
            updates.append("phone = %s")
            params.append(str(phone).strip() or None)

        if email is not None:
            email_str = str(email).strip() or None
            if email_str and not validate_email(email_str):
                return None, "Invalid email address format"
            updates.append("email = %s")
            params.append(email_str)

        if status is not None:
            status_str = str(status).strip()
            if status_str not in ["Active", "Inactive"]:
                return None, "Status must be either 'Active' or 'Inactive'"
            updates.append("status = %s")
            params.append(status_str)

        if "user_id" in data:
            if user_id is None or str(user_id).strip() == "" or str(user_id) == "0":
                updates.append("user_id = %s")
                params.append(None)
            else:
                try:
                    uid = int(user_id)
                except (ValueError, TypeError):
                    return None, "Invalid user_id"

                # Check if user exists and has Supplier role
                cursor.execute("""
                    SELECT u.user_id, r.role_name
                    FROM "Users" u
                    JOIN "Roles" r ON u.role_id = r.role_id
                    WHERE u.user_id = %s
                """, (uid,))
                user_row = cursor.fetchone()
                if not user_row:
                    return None, "Selected user does not exist"
                if user_row[1] != "Supplier":
                    return None, "Selected user does not have the 'Supplier' role"

                # Check if already linked to a different supplier
                cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s AND supplier_id != %s', (uid, supplier_id))
                other_link = cursor.fetchone()
                if other_link:
                    return None, f"User is already linked to supplier #{other_link[0]}"

                updates.append("user_id = %s")
                params.append(uid)

        if not updates:
            return None, "No fields to update"

        params.append(supplier_id)
        update_query = f"""
            UPDATE "Suppliers"
            SET {', '.join(updates)}
            WHERE supplier_id = %s
            RETURNING supplier_id, supplier_name, contact_person, phone, email, status, user_id
        """

        cursor.execute(update_query, tuple(params))
        updated_row = cursor.fetchone()
        conn.commit()

        updated_supplier = {
            "supplier_id": updated_row[0],
            "supplier_name": updated_row[1],
            "contact_person": updated_row[2] or "",
            "phone": updated_row[3] or "",
            "email": updated_row[4] or "",
            "status": updated_row[5],
            "user_id": updated_row[6]
        }

        return updated_supplier, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_supplier(supplier_id):
    """
    Delete or deactivate a supplier.
    If the supplier is referenced in PurchaseOrders, SupplierQuotations, or Shipments,
    soft-deactivates (status = 'Inactive').
    Otherwise hard deletes the record.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existence
        cursor.execute('SELECT supplier_id, supplier_name, status FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
        existing = cursor.fetchone()
        if not existing:
            return None, "Supplier not found"

        # Check references
        cursor.execute('SELECT COUNT(*) FROM "PurchaseOrders" WHERE supplier_id = %s', (supplier_id,))
        po_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM "SupplierQuotations" WHERE supplier_id = %s', (supplier_id,))
        quotation_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM "Shipments" WHERE supplier_id = %s', (supplier_id,))
        shipment_count = cursor.fetchone()[0]

        total_references = po_count + quotation_count + shipment_count

        if total_references > 0:
            # Soft-deactivate to preserve database integrity
            cursor.execute('UPDATE "Suppliers" SET status = %s WHERE supplier_id = %s', ("Inactive", supplier_id))
            conn.commit()
            return {
                "supplier_id": supplier_id,
                "status": "Inactive",
                "deactivated": True,
                "message": f"Supplier has {total_references} related order/quotation records and has been deactivated instead of permanently deleted."
            }, None
        else:
            # Safe to hard delete
            cursor.execute('DELETE FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
            conn.commit()
            return {
                "supplier_id": supplier_id,
                "deleted": True,
                "message": "Supplier deleted successfully."
            }, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
