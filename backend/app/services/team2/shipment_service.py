from datetime import date, datetime
from decimal import Decimal
import random
from app.extensions import get_db_connection


def get_supplier_id_for_user(user_id):
    """
    Look up supplier_id and supplier_name linked to a user_id.
    """
    if not user_id:
        return None, None
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None, None

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT supplier_id, supplier_name FROM "Suppliers" WHERE user_id = %s', (user_id,))
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        return None, None
    except Exception:
        return None, None
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_shipments(user_id=None, role=None, po_id=None, supplier_id_filter=None, status_filter=None, search=None, employee_id_filter=None):
    """
    List shipments with role-based access control.
    - Supplier strictly sees only their own shipments.
    - Employee strictly sees only shipments assigned to them.
    - Owner/Manager can see all shipments, with optional filtering.
    Computes summary KPI stats (ready, in_transit, delivered, delayed, total).
    Includes employee assignment and receiving status.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        resolved_supplier_id = None
        resolved_employee_id = None

        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row:
                return [], {
                    "total_shipments": 0,
                    "ready": 0,
                    "in_transit": 0,
                    "delivered": 0,
                    "delayed": 0
                }, None
            resolved_supplier_id = s_row[0]
        elif role == 'Employee':
            # Strict assignment isolation for employees
            resolved_employee_id = int(user_id)
        else:
            if supplier_id_filter:
                try:
                    resolved_supplier_id = int(supplier_id_filter)
                except (ValueError, TypeError):
                    resolved_supplier_id = None
            if employee_id_filter:
                try:
                    resolved_employee_id = int(employee_id_filter)
                except (ValueError, TypeError):
                    resolved_employee_id = None

        query = """
            SELECT 
                shp.shipment_id,
                shp.shipment_number,
                shp.purchase_order_id,
                shp.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                shp.carrier,
                shp.tracking_number,
                shp.shipping_method,
                shp.status,
                shp.package_count,
                shp.total_weight,
                shp.shipping_notes,
                shp.origin_address,
                shp.destination_address,
                shp.expected_delivery,
                shp.shipped_at,
                shp.delivered_at,
                shp.created_at,
                shp.updated_at,
                po.order_date AS po_order_date,
                po.total_amount AS po_total,
                po.status AS po_status,
                shp.assigned_employee_id,
                u_emp.username AS assigned_employee_name,
                COALESCE(shp.receiving_status, 'Pending Receipt') AS receiving_status,
                COALESCE(st_rec.total_received, 0) AS total_received,
                COALESCE(poi_exp.total_expected, 0) AS total_expected
            FROM "Shipments" shp
            JOIN "Suppliers" s ON shp.supplier_id = s.supplier_id
            JOIN "PurchaseOrders" po ON shp.purchase_order_id = po.purchase_order_id
            LEFT JOIN "Users" u_emp ON shp.assigned_employee_id = u_emp.user_id
            LEFT JOIN (
                SELECT shipment_id, SUM(quantity) AS total_received
                FROM "StockTransactions"
                WHERE transaction_type = 'STOCK_IN' AND shipment_id IS NOT NULL
                GROUP BY shipment_id
            ) st_rec ON shp.shipment_id = st_rec.shipment_id
            LEFT JOIN (
                SELECT purchase_order_id, SUM(quantity) AS total_expected
                FROM "PurchaseOrderItems"
                GROUP BY purchase_order_id
            ) poi_exp ON shp.purchase_order_id = poi_exp.purchase_order_id
            WHERE 1=1
        """
        params = []

        if resolved_supplier_id:
            query += " AND shp.supplier_id = %s"
            params.append(resolved_supplier_id)

        if resolved_employee_id:
            query += " AND shp.assigned_employee_id = %s"
            params.append(resolved_employee_id)

        if po_id:
            try:
                query += " AND shp.purchase_order_id = %s"
                params.append(int(po_id))
            except (ValueError, TypeError):
                pass

        if status_filter and status_filter.strip():
            query += " AND shp.status ILIKE %s"
            params.append(status_filter.strip())

        if search and search.strip():
            search_param = f"%{search.strip()}%"
            query += """
                AND (
                    shp.shipment_number ILIKE %s
                    OR shp.tracking_number ILIKE %s
                    OR shp.carrier ILIKE %s
                    OR s.supplier_name ILIKE %s
                    OR shp.purchase_order_id::text ILIKE %s
                )
            """
            params.extend([search_param, search_param, search_param, search_param, search_param])

        query += " ORDER BY shp.shipment_id DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        shipments = []
        stats = {
            "total_shipments": 0,
            "ready": 0,
            "in_transit": 0,
            "delivered": 0,
            "delayed": 0
        }

        for r in rows:
            st = r[11] or "Ready for Shipment"
            st_lower = st.lower()

            stats["total_shipments"] += 1
            if st_lower in ("ready for shipment", "pending", "created"):
                stats["ready"] += 1
            elif st_lower in ("in transit", "dispatched", "shipped"):
                stats["in_transit"] += 1
            elif st_lower == "delivered":
                stats["delivered"] += 1
            elif st_lower == "delayed":
                stats["delayed"] += 1

            exp_qty = int(r[29] or 0)
            rec_qty = int(r[28] or 0)
            rem_qty = max(0, exp_qty - rec_qty)

            # Determine receiving status
            raw_rec = r[27] or "Pending Receipt"
            if st_lower == "delivered":
                if rec_qty == 0:
                    effective_rec_status = "Pending Receipt"
                elif exp_qty > 0 and rec_qty >= exp_qty:
                    effective_rec_status = "Fully Received"
                elif rec_qty > 0:
                    effective_rec_status = "Partially Received"
                else:
                    effective_rec_status = raw_rec
            else:
                effective_rec_status = "Pending Receipt"

            shipments.append({
                "shipment_id": r[0],
                "shipment_number": r[1],
                "purchase_order_id": r[2],
                "supplier_id": r[3],
                "supplier_name": r[4],
                "contact_person": r[5] or "",
                "supplier_email": r[6] or "",
                "supplier_phone": r[7] or "",
                "carrier": r[8],
                "tracking_number": r[9] or "",
                "shipping_method": r[10] or "Standard Ground",
                "status": st,
                "package_count": r[12] or 1,
                "total_weight": float(r[13]) if r[13] is not None else None,
                "shipping_notes": r[14] or "",
                "origin_address": r[15] or "",
                "destination_address": r[16] or "",
                "expected_delivery": r[17].isoformat() if r[17] else None,
                "shipped_at": r[18].isoformat() if r[18] else None,
                "delivered_at": r[19].isoformat() if r[19] else None,
                "created_at": r[20].isoformat() if r[20] else None,
                "updated_at": r[21].isoformat() if r[21] else None,
                "po_order_date": r[22].isoformat() if r[22] else None,
                "po_total": float(r[23]) if r[23] is not None else 0.0,
                "po_status": r[24] or "",
                "assigned_employee_id": r[25],
                "assigned_employee_name": r[26] or "",
                "receiving_status": effective_rec_status,
                "total_expected_quantity": exp_qty,
                "total_received_quantity": rec_qty,
                "total_remaining_quantity": rem_qty
            })

        return shipments, stats, None

    except Exception as e:
        return None, None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_shipment_by_id(shipment_id, user_id=None, role=None):
    """
    Get shipment details by ID with strict Supplier and Employee isolation.
    Includes joined Purchase Order items with expected, received, and remaining quantities,
    and OrderStatusHistory timeline.
    """
    try:
        shipment_id = int(shipment_id)
    except (ValueError, TypeError):
        return None, "Invalid shipment_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                shp.shipment_id,
                shp.shipment_number,
                shp.purchase_order_id,
                shp.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                shp.carrier,
                shp.tracking_number,
                shp.shipping_method,
                shp.status,
                shp.package_count,
                shp.total_weight,
                shp.shipping_notes,
                shp.origin_address,
                shp.destination_address,
                shp.expected_delivery,
                shp.shipped_at,
                shp.delivered_at,
                shp.created_at,
                shp.updated_at,
                po.order_date AS po_order_date,
                po.total_amount AS po_total,
                po.status AS po_status,
                po.expected_delivery AS po_expected_delivery,
                shp.assigned_employee_id,
                u_emp.username AS assigned_employee_name,
                COALESCE(shp.receiving_status, 'Pending Receipt') AS receiving_status
            FROM "Shipments" shp
            JOIN "Suppliers" s ON shp.supplier_id = s.supplier_id
            JOIN "PurchaseOrders" po ON shp.purchase_order_id = po.purchase_order_id
            LEFT JOIN "Users" u_emp ON shp.assigned_employee_id = u_emp.user_id
            WHERE shp.shipment_id = %s
        """
        cursor.execute(query, (shipment_id,))
        row = cursor.fetchone()

        if not row:
            return None, "Shipment not found"

        supplier_id = row[3]
        po_id = row[2]
        assigned_emp_id = row[26]
        assigned_emp_name = row[27] or ""
        shp_status = row[11] or "Ready for Shipment"

        # Supplier Isolation Check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                return None, "Access denied. You can only view your own shipments."

        # Employee Isolation Check
        if role == 'Employee':
            if not assigned_emp_id or assigned_emp_id != int(user_id):
                return None, "Access denied. You can only view shipments assigned to you."

        # Fetch PO items with expected and received quantity computation
        cursor.execute("""
            SELECT poi.product_id, p.product_name, p.sku, poi.quantity, poi.unit_price, poi.subtotal
            FROM "PurchaseOrderItems" poi
            JOIN "Products" p ON poi.product_id = p.product_id
            WHERE poi.purchase_order_id = %s
            ORDER BY poi.purchase_order_item_id ASC
        """, (po_id,))
        po_items_raw = cursor.fetchall()

        po_items = []
        total_exp = 0
        total_rec = 0

        for ir in po_items_raw:
            pid = ir[0]
            pname = ir[1]
            psku = ir[2] or ""
            poi_qty = ir[3]
            uprice = float(ir[4]) if ir[4] is not None else 0.0
            subtot = float(ir[5]) if ir[5] is not None else 0.0

            # Check approved quotation for exact approved quantity
            cursor.execute("""
                SELECT quantity FROM "SupplierQuotations"
                WHERE purchase_order_id = %s AND product_id = %s AND status IN ('Approved', 'Accepted')
                LIMIT 1
            """, (po_id, pid))
            q_row = cursor.fetchone()
            expected_qty = q_row[0] if q_row else poi_qty

            # Check received quantity for this shipment and product
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM "StockTransactions"
                WHERE shipment_id = %s AND product_id = %s AND transaction_type = 'STOCK_IN'
            """, (shipment_id, pid))
            received_qty = cursor.fetchone()[0]

            remaining_qty = max(0, expected_qty - received_qty)
            total_exp += expected_qty
            total_rec += received_qty

            if received_qty == 0:
                item_rec_status = "Pending Receipt"
            elif received_qty < expected_qty:
                item_rec_status = "Partially Received"
            else:
                item_rec_status = "Fully Received"

            po_items.append({
                "product_id": pid,
                "product_name": pname,
                "sku": psku,
                "quantity": expected_qty,
                "expected_quantity": expected_qty,
                "received_quantity": received_qty,
                "remaining_quantity": remaining_qty,
                "receiving_status": item_rec_status,
                "unit_price": uprice,
                "subtotal": subtot
            })

        total_rem = max(0, total_exp - total_rec)
        if shp_status.lower() == "delivered":
            if total_rec == 0:
                overall_rec_status = "Pending Receipt"
            elif total_exp > 0 and total_rec >= total_exp:
                overall_rec_status = "Fully Received"
            else:
                overall_rec_status = "Partially Received"
        else:
            overall_rec_status = "Pending Receipt"

        # Fetch OrderStatusHistory timeline for this shipment
        cursor.execute("""
            SELECT history_id, status, previous_status, action, location, notes, changed_by, created_at
            FROM "OrderStatusHistory"
            WHERE shipment_id = %s OR (purchase_order_id = %s AND action ILIKE 'SHIPMENT%%')
            ORDER BY history_id ASC
        """, (shipment_id, po_id))
        history = []
        for hr in cursor.fetchall():
            history.append({
                "history_id": hr[0],
                "status": hr[1],
                "previous_status": hr[2] or "",
                "action": hr[3],
                "location": hr[4] or "",
                "notes": hr[5] or "",
                "changed_by": hr[6] or "",
                "created_at": hr[7].isoformat() if hr[7] else None
            })

        data = {
            "shipment_id": row[0],
            "shipment_number": row[1],
            "purchase_order_id": row[2],
            "supplier_id": row[3],
            "supplier_name": row[4],
            "contact_person": row[5] or "",
            "supplier_email": row[6] or "",
            "supplier_phone": row[7] or "",
            "carrier": row[8],
            "tracking_number": row[9] or "",
            "shipping_method": row[10] or "Standard Ground",
            "status": shp_status,
            "package_count": row[12] or 1,
            "total_weight": float(row[13]) if row[13] is not None else None,
            "shipping_notes": row[14] or "",
            "origin_address": row[15] or "",
            "destination_address": row[16] or "",
            "expected_delivery": row[17].isoformat() if row[17] else None,
            "shipped_at": row[18].isoformat() if row[18] else None,
            "delivered_at": row[19].isoformat() if row[19] else None,
            "created_at": row[20].isoformat() if row[20] else None,
            "updated_at": row[21].isoformat() if row[21] else None,
            "assigned_employee_id": assigned_emp_id,
            "assigned_employee_name": assigned_emp_name,
            "receiving_status": overall_rec_status,
            "total_expected_quantity": total_exp,
            "total_received_quantity": total_rec,
            "total_remaining_quantity": total_rem,
            "purchase_order": {
                "purchase_order_id": po_id,
                "order_date": row[22].isoformat() if row[22] else None,
                "total_amount": float(row[23]) if row[23] is not None else 0.0,
                "status": row[24] or "",
                "expected_delivery": row[25].isoformat() if row[25] else None,
                "items": po_items
            },
            "status_history": history
        }

        return data, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def assign_employee(shipment_id, employee_id, user_id=None, role=None, username=None):
    """
    Assign or reassign an active employee to a shipment.
    Allowed roles: Owner, Manager.
    Validations:
      - Shipment exists.
      - Shipment not Cancelled.
      - Shipment not already Fully Received.
      - Employee exists, has 'Employee' role, and is 'Active'.
      - Records OrderStatusHistory entry.
    """
    if employee_id is None or employee_id == "":
        return None, "employee_id is required"
    try:
        shipment_id = int(shipment_id)
    except (ValueError, TypeError):
        return None, "Invalid shipment_id"
    try:
        employee_id = int(employee_id)
    except (ValueError, TypeError):
        return None, "employee_id must be a valid integer"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Fetch shipment
        cursor.execute("""
            SELECT shipment_id, shipment_number, purchase_order_id, supplier_id, status, assigned_employee_id, COALESCE(receiving_status, 'Pending Receipt')
            FROM "Shipments"
            WHERE shipment_id = %s
        """, (shipment_id,))
        shp = cursor.fetchone()
        if not shp:
            conn.rollback()
            return None, "Shipment not found"

        shipment_num = shp[1]
        po_id = shp[2]
        supplier_id = shp[3]
        current_status = shp[4]
        current_assigned_id = shp[5]
        current_rec_status = shp[6]

        if current_status == 'Cancelled':
            conn.rollback()
            return None, "Cannot assign employee to a cancelled shipment"

        # Check if already fully received
        cursor.execute("""
            SELECT COALESCE(SUM(st.quantity), 0)
            FROM "StockTransactions" st
            WHERE st.shipment_id = %s AND st.transaction_type = 'STOCK_IN'
        """, (shipment_id,))
        rec_sum = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(poi.quantity), 0)
            FROM "PurchaseOrderItems" poi
            WHERE poi.purchase_order_id = %s
        """, (po_id,))
        exp_sum = cursor.fetchone()[0]

        if current_rec_status == 'Fully Received' or (exp_sum > 0 and rec_sum >= exp_sum):
            conn.rollback()
            return None, "Cannot reassign employee on a fully received shipment"

        # 2. Fetch and validate employee
        cursor.execute("""
            SELECT u.user_id, u.username, r.role_name, u.status
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE u.user_id = %s
        """, (employee_id,))
        emp = cursor.fetchone()
        if not emp:
            conn.rollback()
            return None, "Employee not found"

        emp_username = emp[1]
        emp_role = emp[2]
        emp_status = emp[3]

        if emp_role != 'Employee':
            conn.rollback()
            return None, f"Selected user '{emp_username}' does not have the Employee role"

        if emp_status != 'Active':
            conn.rollback()
            return None, f"Selected employee '{emp_username}' account is inactive"

        # 3. Update Shipment
        cursor.execute("""
            UPDATE "Shipments"
            SET assigned_employee_id = %s,
                updated_at = NOW()
            WHERE shipment_id = %s
        """, (employee_id, shipment_id))

        # 4. Insert into OrderStatusHistory
        notes = f"Employee {emp_username} (ID: {employee_id}) assigned to shipment {shipment_num}"
        cursor.execute("""
            INSERT INTO "OrderStatusHistory" (
                purchase_order_id,
                shipment_id,
                supplier_id,
                status,
                previous_status,
                action,
                location,
                notes,
                changed_by,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            po_id,
            shipment_id,
            supplier_id,
            current_status,
            current_status,
            "EMPLOYEE_ASSIGNED",
            "Receiving Dock",
            notes,
            username or role or "Manager"
        ))

        conn.commit()

        return {
            "shipment_id": shipment_id,
            "shipment_number": shipment_num,
            "assigned_employee_id": employee_id,
            "assigned_employee_name": emp_username,
            "status": current_status,
            "receiving_status": current_rec_status,
            "message": f"Employee {emp_username} assigned successfully to shipment {shipment_num}"
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


def create_shipment(data, user_id, role, username):
    """
    Create and dispatch a shipment for a valid procurement transaction.
    Validations:
    - PO exists and is valid.
    - Supplier owns the PO.
    - PO was accepted by supplier.
    - An approved quotation exists if required by procurement workflow.
    - Required fields: carrier, tracking_number.
    - Sets initial status ('Ready for Shipment', 'Dispatched', or 'In Transit').
    - Inserts entry into OrderStatusHistory.
    """
    if not data or not isinstance(data, dict):
        return None, "Request body is required"

    po_id = data.get("purchase_order_id")
    if not po_id:
        return None, "purchase_order_id is required"

    try:
        po_id = int(po_id)
    except (ValueError, TypeError):
        return None, "purchase_order_id must be a valid integer"

    carrier = data.get("carrier")
    if not carrier or not str(carrier).strip():
        carrier = "Standard Logistics"
    else:
        carrier = str(carrier).strip()

    tracking_number = data.get("tracking_number")
    if tracking_number:
        tracking_number = str(tracking_number).strip()

    shipping_method = data.get("shipping_method") or "Standard Ground"
    package_count = data.get("package_count", 1)
    try:
        package_count = int(package_count)
        if package_count <= 0:
            return None, "package_count must be greater than zero"
    except (ValueError, TypeError):
        return None, "package_count must be a valid integer"

    total_weight = data.get("total_weight")
    if total_weight is not None:
        try:
            total_weight = Decimal(str(total_weight))
            if total_weight < 0:
                return None, "total_weight cannot be negative"
        except Exception:
            return None, "total_weight must be a valid number"

    shipping_notes = data.get("shipping_notes") or ""
    origin_address = data.get("origin_address") or "Central Fulfillment Dock"
    destination_address = data.get("destination_address") or "Central Inventory Receiving Bay"
    expected_delivery = data.get("expected_delivery")

    raw_status = data.get("status", "Ready for Shipment")
    allowed_initial = ("Ready for Shipment", "Dispatched", "In Transit")
    if raw_status not in allowed_initial:
        raw_status = "Ready for Shipment"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Resolve Supplier ID
        supplier_id = None
        supplier_name = None
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id, supplier_name FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row:
                conn.rollback()
                return None, "No supplier profile linked to authenticated user"
            supplier_id = s_row[0]
            supplier_name = s_row[1]
        else:
            supplier_id = data.get("supplier_id")
            if not supplier_id:
                cursor.execute('SELECT supplier_id FROM "PurchaseOrders" WHERE purchase_order_id = %s', (po_id,))
                po_s = cursor.fetchone()
                if not po_s:
                    conn.rollback()
                    return None, "Purchase order not found"
                supplier_id = po_s[0]
            else:
                try:
                    supplier_id = int(supplier_id)
                except (ValueError, TypeError):
                    conn.rollback()
                    return None, "supplier_id must be a valid integer"
            cursor.execute('SELECT supplier_name FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
            sn_row = cursor.fetchone()
            supplier_name = sn_row[0] if sn_row else f"Supplier {supplier_id}"

        # 2. Check Purchase Order ownership and eligibility
        cursor.execute("""
            SELECT purchase_order_id, supplier_id, status, supplier_response
            FROM "PurchaseOrders"
            WHERE purchase_order_id = %s
        """, (po_id,))
        po_row = cursor.fetchone()

        if not po_row:
            conn.rollback()
            return None, "Purchase order not found"

        if po_row[1] != supplier_id:
            conn.rollback()
            return None, "Purchase order does not belong to this supplier"

        po_status = (po_row[2] or "").strip()
        po_response = (po_row[3] or "").strip()
        if po_status == 'Rejected' or po_response == 'Rejected':
            conn.rollback()
            return None, "Cannot create shipment for a rejected Purchase Order"

        if po_response != 'Accepted' and po_status != 'Accepted':
            conn.rollback()
            return None, "Cannot create shipment for an unaccepted Purchase Order"

        # 3. Check for approved quotation if quotations exist for this PO
        cursor.execute("""
            SELECT quotation_id, supplier_id, status
            FROM "SupplierQuotations"
            WHERE purchase_order_id = %s
        """, (po_id,))
        quotes = cursor.fetchall()
        if quotes:
            approved_quote = [q for q in quotes if q[2] in ('Approved', 'Accepted')]
            if not approved_quote:
                conn.rollback()
                return None, "Cannot create shipment: Manager/Owner quotation approval is required for this Purchase Order"
            if approved_quote[0][1] != supplier_id:
                conn.rollback()
                return None, "Cannot create shipment: Approved quotation belongs to a different supplier"

        # 4. Generate unique shipment number
        cursor.execute('SELECT COALESCE(MAX(shipment_id), 0) + 1 FROM "Shipments"')
        next_sid = cursor.fetchone()[0]
        rand_suffix = random.randint(100, 999)
        shipment_number = f"SHP-PO{po_id:04d}-{next_sid:03d}"

        # If tracking number wasn't provided, generate one
        if not tracking_number:
            tracking_number = f"TRK-{po_id:04d}-{random.randint(10000, 99999)}"

        shipped_at = datetime.now() if raw_status in ("Dispatched", "In Transit") else None

        # 5. Insert Shipment
        cursor.execute("""
            INSERT INTO "Shipments" (
                shipment_number,
                purchase_order_id,
                supplier_id,
                carrier,
                tracking_number,
                shipping_method,
                status,
                package_count,
                total_weight,
                shipping_notes,
                origin_address,
                destination_address,
                expected_delivery,
                shipped_at,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING shipment_id
        """, (
            shipment_number,
            po_id,
            supplier_id,
            carrier,
            tracking_number,
            shipping_method,
            raw_status,
            package_count,
            total_weight,
            shipping_notes,
            origin_address,
            destination_address,
            expected_delivery if expected_delivery else None,
            shipped_at
        ))
        new_shipment_id = cursor.fetchone()[0]

        # 6. Insert OrderStatusHistory entry
        cursor.execute("""
            INSERT INTO "OrderStatusHistory" (
                purchase_order_id,
                shipment_id,
                supplier_id,
                status,
                previous_status,
                action,
                location,
                notes,
                changed_by,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            po_id,
            new_shipment_id,
            supplier_id,
            raw_status,
            "Ready for Shipment" if raw_status != "Ready for Shipment" else "PO Accepted",
            "SHIPMENT_CREATED",
            origin_address,
            f"Shipment {shipment_number} created with carrier {carrier} (Tracking: {tracking_number})",
            username or supplier_name
        ))

        conn.commit()

        result = {
            "shipment_id": new_shipment_id,
            "shipment_number": shipment_number,
            "purchase_order_id": po_id,
            "supplier_id": supplier_id,
            "carrier": carrier,
            "tracking_number": tracking_number,
            "shipping_method": shipping_method,
            "status": raw_status,
            "package_count": package_count,
            "total_weight": float(total_weight) if total_weight is not None else None,
            "expected_delivery": str(expected_delivery) if expected_delivery else None,
            "shipped_at": shipped_at.isoformat() if shipped_at else None
        }
        return result, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_shipment_details(shipment_id, data, user_id, role):
    """
    Update carrier, tracking, package count, weight, notes or expected delivery.
    Suppliers can only update their own shipments.
    Cannot edit a Delivered or Cancelled shipment.
    """
    try:
        shipment_id = int(shipment_id)
    except (ValueError, TypeError):
        return None, "Invalid shipment_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT shipment_id, supplier_id, status, carrier, tracking_number, shipping_method, 
                   package_count, total_weight, shipping_notes, origin_address, destination_address, expected_delivery
            FROM "Shipments"
            WHERE shipment_id = %s
        """, (shipment_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Shipment not found"

        supplier_id = row[1]
        current_status = row[2] or "Ready for Shipment"

        # Supplier isolation check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                conn.rollback()
                return None, "Access denied. You can only update your own shipments."

        if current_status in ('Delivered', 'Cancelled'):
            conn.rollback()
            return None, f"Cannot modify shipment in '{current_status}' status"

        carrier = data.get("carrier", row[3])
        tracking_number = data.get("tracking_number", row[4])
        shipping_method = data.get("shipping_method", row[5])
        package_count = data.get("package_count", row[6])
        if package_count:
            try:
                package_count = int(package_count)
                if package_count <= 0:
                    conn.rollback()
                    return None, "package_count must be greater than zero"
            except (ValueError, TypeError):
                conn.rollback()
                return None, "package_count must be an integer"

        total_weight = data.get("total_weight", row[7])
        if total_weight is not None:
            try:
                total_weight = Decimal(str(total_weight))
                if total_weight < 0:
                    conn.rollback()
                    return None, "total_weight cannot be negative"
            except Exception:
                conn.rollback()
                return None, "total_weight must be a valid number"

        shipping_notes = data.get("shipping_notes", row[8])
        origin_address = data.get("origin_address", row[9])
        destination_address = data.get("destination_address", row[10])
        expected_delivery = data.get("expected_delivery", row[11])

        cursor.execute("""
            UPDATE "Shipments"
            SET carrier = %s,
                tracking_number = %s,
                shipping_method = %s,
                package_count = %s,
                total_weight = %s,
                shipping_notes = %s,
                origin_address = %s,
                destination_address = %s,
                expected_delivery = %s,
                updated_at = NOW()
            WHERE shipment_id = %s
        """, (
            carrier,
            tracking_number,
            shipping_method,
            package_count,
            total_weight,
            shipping_notes,
            origin_address,
            destination_address,
            expected_delivery if expected_delivery else None,
            shipment_id
        ))

        conn.commit()
        return {
            "shipment_id": shipment_id,
            "carrier": carrier,
            "tracking_number": tracking_number,
            "shipping_method": shipping_method,
            "package_count": package_count,
            "total_weight": float(total_weight) if total_weight is not None else None,
            "status": current_status
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


def update_shipment_status(shipment_id, new_status, location=None, notes=None, user_id=None, role=None, username=None):
    """
    Update shipment status with strict lifecycle transition rules.
    Allowed Transitions:
      'Ready for Shipment' -> 'Dispatched', 'In Transit', 'Cancelled'
      'Dispatched'         -> 'In Transit', 'Delayed', 'Delivered', 'Cancelled'
      'In Transit'          -> 'Delivered', 'Delayed', 'Cancelled'
      'Delayed'             -> 'In Transit', 'Delivered', 'Cancelled'
      'Delivered'           -> Terminal state (no further transitions)
      'Cancelled'           -> Terminal state (no further transitions)

    IMPORTANT INVENTORY SAFETY:
      When status becomes 'Delivered', Inventory is NOT modified.
      (Inventory modification is reserved for Step 6 Stock-In).
    """
    if not new_status or not str(new_status).strip():
        return None, "new_status is required"
    new_status = str(new_status).strip()

    valid_statuses = ("Ready for Shipment", "Dispatched", "In Transit", "Delivered", "Delayed", "Cancelled")
    if new_status not in valid_statuses:
        return None, f"Invalid status '{new_status}'. Allowed values: {', '.join(valid_statuses)}"

    try:
        shipment_id = int(shipment_id)
    except (ValueError, TypeError):
        return None, "Invalid shipment_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT shp.shipment_id, shp.purchase_order_id, shp.supplier_id, shp.status, shp.shipment_number, 
                   shp.shipped_at, shp.delivered_at, s.supplier_name
            FROM "Shipments" shp
            JOIN "Suppliers" s ON shp.supplier_id = s.supplier_id
            WHERE shp.shipment_id = %s
        """, (shipment_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Shipment not found"

        po_id = row[1]
        supplier_id = row[2]
        current_status = row[3] or "Ready for Shipment"
        shipment_num = row[4]
        existing_shipped_at = row[5]
        existing_delivered_at = row[6]
        supplier_name = row[7]

        # Supplier isolation check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                conn.rollback()
                return None, "Access denied. You can only update your own shipments."

        # If same status, idempotent return
        if current_status.lower() == new_status.lower():
            conn.rollback()
            return {"shipment_id": shipment_id, "status": current_status, "message": "Status unchanged"}, None

        # Validate allowed transitions
        allowed_transitions = {
            "ready for shipment": ["dispatched", "in transit", "cancelled"],
            "dispatched": ["in transit", "delayed", "delivered", "cancelled"],
            "in transit": ["delivered", "delayed", "cancelled"],
            "delayed": ["in transit", "delivered", "cancelled"],
            "delivered": [],  # Terminal
            "cancelled": []   # Terminal
        }

        curr_lower = current_status.lower()
        new_lower = new_status.lower()

        if curr_lower in allowed_transitions and new_lower not in allowed_transitions[curr_lower]:
            conn.rollback()
            return None, f"Invalid status transition from '{current_status}' to '{new_status}'"

        # Determine timestamps
        shipped_at = existing_shipped_at
        if new_status in ("Dispatched", "In Transit") and not existing_shipped_at:
            shipped_at = datetime.now()

        delivered_at = existing_delivered_at
        if new_status == "Delivered" and not existing_delivered_at:
            delivered_at = datetime.now()

        # Update Shipment
        cursor.execute("""
            UPDATE "Shipments"
            SET status = %s,
                shipped_at = %s,
                delivered_at = %s,
                updated_at = NOW()
            WHERE shipment_id = %s
        """, (new_status, shipped_at, delivered_at, shipment_id))

        # If delivered, update PurchaseOrders status to Delivered
        if new_status == "Delivered":
            cursor.execute("""
                UPDATE "PurchaseOrders"
                SET status = 'Delivered'
                WHERE purchase_order_id = %s
            """, (po_id,))

        # Insert OrderStatusHistory entry
        action_name = f"SHIPMENT_{new_status.upper().replace(' ', '_')}"
        status_notes = notes or f"Shipment {shipment_num} status updated to {new_status}"

        cursor.execute("""
            INSERT INTO "OrderStatusHistory" (
                purchase_order_id,
                shipment_id,
                supplier_id,
                status,
                previous_status,
                action,
                location,
                notes,
                changed_by,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            po_id,
            shipment_id,
            supplier_id,
            new_status,
            current_status,
            action_name,
            location or "In Transit Hub",
            status_notes,
            username or supplier_name or role
        ))

        conn.commit()

        return {
            "shipment_id": shipment_id,
            "shipment_number": shipment_num,
            "previous_status": current_status,
            "status": new_status,
            "shipped_at": shipped_at.isoformat() if shipped_at else None,
            "delivered_at": delivered_at.isoformat() if delivered_at else None,
            "message": f"Shipment status updated to '{new_status}'"
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
