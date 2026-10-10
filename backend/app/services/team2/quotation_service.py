from datetime import date, datetime
from decimal import Decimal
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


def get_quotations(user_id=None, role=None, po_id=None, supplier_id_filter=None, status_filter=None, search=None):
    """
    List quotations with role-based access control.
    - Supplier strictly sees only their own quotations.
    - Owner/Manager can see all quotations with optional filtering by PO, supplier, status, or search.
    Computes summary statistics for KPI cards.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        resolved_supplier_id = None
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row:
                return [], {
                    "drafts": 0,
                    "submitted": 0,
                    "approved": 0,
                    "rejected": 0,
                    "total_quotations": 0,
                    "total_value": 0.0
                }, None
            resolved_supplier_id = s_row[0]
        elif supplier_id_filter:
            try:
                resolved_supplier_id = int(supplier_id_filter)
            except (ValueError, TypeError):
                resolved_supplier_id = None

        query = """
            SELECT 
                q.quotation_id,
                q.quotation_number,
                q.purchase_order_id,
                q.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                q.product_id,
                p.product_name,
                p.sku AS product_sku,
                q.quotation_date,
                q.quoted_price,
                q.quantity,
                q.valid_until,
                q.status,
                COALESCE(q.total_amount, (q.quoted_price * q.quantity)) AS line_total,
                q.notes,
                q.submitted_at,
                q.approved_at,
                q.approved_by,
                u.username AS approved_by_username,
                q.rejection_reason,
                po.order_date AS po_order_date,
                po.total_amount AS po_total,
                po.status AS po_status
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            JOIN "Products" p ON q.product_id = p.product_id
            LEFT JOIN "PurchaseOrders" po ON q.purchase_order_id = po.purchase_order_id
            LEFT JOIN "Users" u ON q.approved_by = u.user_id
            WHERE 1=1
        """
        params = []

        if resolved_supplier_id:
            query += " AND q.supplier_id = %s"
            params.append(resolved_supplier_id)

        if po_id:
            try:
                query += " AND q.purchase_order_id = %s"
                params.append(int(po_id))
            except (ValueError, TypeError):
                pass

        if status_filter and status_filter.strip():
            query += " AND q.status ILIKE %s"
            params.append(status_filter.strip())

        if search and search.strip():
            search_param = f"%{search.strip()}%"
            query += """
                AND (
                    q.quotation_id::text ILIKE %s
                    OR q.quotation_number ILIKE %s
                    OR s.supplier_name ILIKE %s
                    OR p.product_name ILIKE %s
                    OR p.sku ILIKE %s
                    OR q.purchase_order_id::text ILIKE %s
                )
            """
            params.extend([search_param, search_param, search_param, search_param, search_param, search_param])

        query += " ORDER BY q.quotation_id DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        quotations = []
        stats = {
            "drafts": 0,
            "submitted": 0,
            "approved": 0,
            "rejected": 0,
            "total_quotations": 0,
            "total_value": 0.0
        }

        for r in rows:
            qid = r[0]
            q_num = r[1] or f"QT-2026-{qid:04d}"
            p_order_id = r[2]
            s_id = r[3]
            s_name = r[4]
            c_person = r[5] or ""
            s_email = r[6] or ""
            s_phone = r[7] or ""
            prod_id = r[8]
            prod_name = r[9]
            prod_sku = r[10] or ""
            q_date = r[11].isoformat() if r[11] else None
            q_price = float(r[12]) if r[12] is not None else 0.0
            q_qty = int(r[13]) if r[13] is not None else 0
            v_until = r[14].isoformat() if r[14] else None
            st = r[15] or "Pending"
            line_tot = float(r[16]) if r[16] is not None else round(q_price * q_qty, 2)
            notes = r[17] or ""
            sub_at = r[18].isoformat() if r[18] else None
            app_at = r[19].isoformat() if r[19] else None
            app_by = r[20]
            app_by_uname = r[21] or ""
            rej_reason = r[22] or ""
            po_ord_date = r[23].isoformat() if r[23] else None
            po_tot = float(r[24]) if r[24] is not None else 0.0
            po_st = r[25] or ""

            # Update stats
            stats["total_quotations"] += 1
            st_lower = st.lower()
            if st_lower == "draft":
                stats["drafts"] += 1
            elif st_lower in ("submitted", "pending", "under review"):
                stats["submitted"] += 1
                stats["total_value"] += line_tot
            elif st_lower in ("approved", "accepted"):
                stats["approved"] += 1
                stats["total_value"] += line_tot
            elif st_lower in ("rejected", "expired", "revision"):
                stats["rejected"] += 1

            quotations.append({
                "quotation_id": qid,
                "quotation_number": q_num,
                "purchase_order_id": p_order_id,
                "supplier_id": s_id,
                "supplier_name": s_name,
                "contact_person": c_person,
                "supplier_email": s_email,
                "supplier_phone": s_phone,
                "product_id": prod_id,
                "product_name": prod_name,
                "product_sku": prod_sku,
                "quotation_date": q_date,
                "quoted_price": q_price,
                "quantity": q_qty,
                "total_amount": line_tot,
                "valid_until": v_until,
                "status": st,
                "notes": notes,
                "submitted_at": sub_at,
                "approved_at": app_at,
                "approved_by": app_by,
                "approved_by_username": app_by_uname,
                "rejection_reason": rej_reason,
                "po_order_date": po_ord_date,
                "po_total": po_tot,
                "po_status": po_st
            })

        stats["total_value"] = round(stats["total_value"], 2)
        return quotations, stats, None

    except Exception as e:
        return None, None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_quotation_by_id(quotation_id, user_id=None, role=None):
    """
    Get quotation details by ID with strict Supplier isolation.
    """
    try:
        quotation_id = int(quotation_id)
    except (ValueError, TypeError):
        return None, "Invalid quotation_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                q.quotation_id,
                q.quotation_number,
                q.purchase_order_id,
                q.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                q.product_id,
                p.product_name,
                p.sku AS product_sku,
                p.selling_price AS product_standard_price,
                q.quotation_date,
                q.quoted_price,
                q.quantity,
                q.valid_until,
                q.status,
                COALESCE(q.total_amount, (q.quoted_price * q.quantity)) AS line_total,
                q.notes,
                q.submitted_at,
                q.approved_at,
                q.approved_by,
                u.username AS approved_by_username,
                q.rejection_reason,
                po.order_date AS po_order_date,
                po.expected_delivery AS po_expected_delivery,
                po.total_amount AS po_total,
                po.status AS po_status,
                poi.quantity AS original_po_quantity,
                poi.unit_price AS original_po_unit_price
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            JOIN "Products" p ON q.product_id = p.product_id
            LEFT JOIN "PurchaseOrders" po ON q.purchase_order_id = po.purchase_order_id
            LEFT JOIN "PurchaseOrderItems" poi ON (po.purchase_order_id = poi.purchase_order_id AND q.product_id = poi.product_id)
            LEFT JOIN "Users" u ON q.approved_by = u.user_id
            WHERE q.quotation_id = %s
        """
        cursor.execute(query, (quotation_id,))
        row = cursor.fetchone()

        if not row:
            return None, "Quotation not found"

        supplier_id = row[3]

        # Supplier Isolation Check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                return None, "Access denied. You can only access your own quotations."

        qid = row[0]
        q_num = row[1] or f"QT-2026-{qid:04d}"

        data = {
            "quotation_id": qid,
            "quotation_number": q_num,
            "purchase_order_id": row[2],
            "supplier_id": row[3],
            "supplier_name": row[4],
            "contact_person": row[5] or "",
            "supplier_email": row[6] or "",
            "supplier_phone": row[7] or "",
            "product_id": row[8],
            "product_name": row[9],
            "product_sku": row[10] or "",
            "product_standard_price": float(row[11]) if row[11] is not None else 0.0,
            "quotation_date": row[12].isoformat() if row[12] else None,
            "quoted_price": float(row[13]) if row[13] is not None else 0.0,
            "quantity": int(row[14]) if row[14] is not None else 0,
            "valid_until": row[15].isoformat() if row[15] else None,
            "status": row[16] or "Pending",
            "total_amount": float(row[17]) if row[17] is not None else round(float(row[13]) * int(row[14]), 2),
            "notes": row[18] or "",
            "submitted_at": row[19].isoformat() if row[19] else None,
            "approved_at": row[20].isoformat() if row[20] else None,
            "approved_by": row[21],
            "approved_by_username": row[22] or "",
            "rejection_reason": row[23] or "",
            "po_order_date": row[24].isoformat() if row[24] else None,
            "po_expected_delivery": row[25].isoformat() if row[25] else None,
            "po_total": float(row[26]) if row[26] is not None else 0.0,
            "po_status": row[27] or "",
            "original_po_quantity": int(row[28]) if row[28] is not None else None,
            "original_po_unit_price": float(row[29]) if row[29] is not None else None
        }

        return data, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_quotation(data, user_id, role, username):
    """
    Create a new quotation for an accepted Purchase Order.
    Supplier can create for their own accepted PO only.
    Supports single-item or multi-item payload.
    Original PO quantities are NOT modified.
    """
    if not data or not isinstance(data, dict):
        return None, "Request body is required"

    po_id = data.get("purchase_order_id")
    if not po_id:
        return None, "purchase_order_id is required"

    try:
        po_id = int(po_id)
    except (ValueError, TypeError):
        return None, "purchase_order_id must be an integer"

    notes = data.get("notes") or ""
    valid_until = data.get("valid_until")
    raw_status = data.get("status", "Submitted")
    initial_status = "Draft" if str(raw_status).strip().lower() == "draft" else "Submitted"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Resolve Supplier ID
        supplier_id = None
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
                # If manager/owner creating on behalf, resolve from PO
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
                    return None, "supplier_id must be an integer"
            cursor.execute('SELECT supplier_name FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
            sn_row = cursor.fetchone()
            supplier_name = sn_row[0] if sn_row else f"Supplier {supplier_id}"

        # 2. Check Purchase Order ownership and status
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

        # PO must have been accepted by supplier
        po_sup_resp = (po_row[3] or "").strip()
        po_status = (po_row[2] or "").strip()
        if po_sup_resp != 'Accepted' and po_status != 'Accepted':
            conn.rollback()
            return None, "Quotations can only be created for accepted Purchase Orders"

        # Check if PO already has an approved quotation
        cursor.execute("""
            SELECT quotation_id FROM "SupplierQuotations"
            WHERE purchase_order_id = %s AND status IN ('Approved', 'Accepted')
        """, (po_id,))
        if cursor.fetchone():
            conn.rollback()
            return None, "This Purchase Order already has an approved quotation"

        # 3. Parse items (either single item fields or 'items' list)
        items = []
        if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 0:
            items = data["items"]
        elif "product_id" in data:
            items = [{
                "product_id": data.get("product_id"),
                "quantity": data.get("quantity"),
                "quoted_price": data.get("quoted_price")
            }]
        else:
            conn.rollback()
            return None, "Quotation must contain 'product_id' with 'quantity' and 'quoted_price', or an 'items' array"

        # Fetch PO items to validate products
        cursor.execute("""
            SELECT poi.product_id, p.product_name, poi.quantity, poi.unit_price
            FROM "PurchaseOrderItems" poi
            JOIN "Products" p ON poi.product_id = p.product_id
            WHERE poi.purchase_order_id = %s
        """, (po_id,))
        po_items_map = {row[0]: {"name": row[1], "po_qty": row[2], "po_price": row[3]} for row in cursor.fetchall()}

        validated_items = []
        for idx, item in enumerate(items, 1):
            if not isinstance(item, dict):
                conn.rollback()
                return None, f"Item #{idx} is invalid"

            prod_id = item.get("product_id")
            if not prod_id:
                conn.rollback()
                return None, f"Item #{idx}: product_id is required"
            try:
                prod_id = int(prod_id)
            except (ValueError, TypeError):
                conn.rollback()
                return None, f"Item #{idx}: product_id must be an integer"

            if prod_id not in po_items_map:
                conn.rollback()
                return None, f"Item #{idx}: Product ID {prod_id} is not part of Purchase Order #{po_id}"

            # Validate quantity (> 0)
            qty_val = item.get("quantity")
            if qty_val is None:
                conn.rollback()
                return None, f"Item #{idx}: quantity is required"
            try:
                qty = int(qty_val)
            except (ValueError, TypeError):
                conn.rollback()
                return None, f"Item #{idx}: quantity must be a positive integer"
            if qty <= 0:
                conn.rollback()
                return None, f"Item #{idx}: quantity must be greater than zero"

            # Validate quoted_price (>= 0)
            price_val = item.get("quoted_price")
            if price_val is None:
                # default to original po price or product price
                price_val = po_items_map[prod_id]["po_price"]
            try:
                unit_price = Decimal(str(price_val))
            except Exception:
                conn.rollback()
                return None, f"Item #{idx}: quoted_price is invalid"
            if unit_price < 0:
                conn.rollback()
                return None, f"Item #{idx}: quoted_price cannot be negative"

            subtotal = Decimal(str(round(qty * float(unit_price), 2)))
            validated_items.append({
                "product_id": prod_id,
                "product_name": po_items_map[prod_id]["name"],
                "quantity": qty,
                "quoted_price": unit_price,
                "total_amount": subtotal
            })

        # 4. Generate common quotation number if multiple items, or per submission
        cursor.execute('SELECT COALESCE(MAX(quotation_id), 0) + 1 FROM "SupplierQuotations"')
        next_id = cursor.fetchone()[0]
        quotation_num = f"QT-2026-{next_id:04d}"

        submitted_timestamp = datetime.now() if initial_status == "Submitted" else None

        created_quotations = []
        for vi in validated_items:
            cursor.execute("""
                INSERT INTO "SupplierQuotations" (
                    supplier_id,
                    product_id,
                    quotation_date,
                    quoted_price,
                    quantity,
                    valid_until,
                    status,
                    purchase_order_id,
                    quotation_number,
                    notes,
                    total_amount,
                    submitted_at
                )
                VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING quotation_id
            """, (
                supplier_id,
                vi["product_id"],
                vi["quoted_price"],
                vi["quantity"],
                valid_until if valid_until else None,
                initial_status,
                po_id,
                quotation_num,
                notes,
                vi["total_amount"],
                submitted_timestamp
            ))
            new_qid = cursor.fetchone()[0]
            created_quotations.append({
                "quotation_id": new_qid,
                "quotation_number": quotation_num,
                "purchase_order_id": po_id,
                "supplier_id": supplier_id,
                "product_id": vi["product_id"],
                "product_name": vi["product_name"],
                "quantity": vi["quantity"],
                "quoted_price": float(vi["quoted_price"]),
                "total_amount": float(vi["total_amount"]),
                "status": initial_status
            })

        # 5. Insert OrderStatusHistory entry if submitted
        if initial_status == "Submitted":
            cursor.execute("""
                INSERT INTO "OrderStatusHistory" (
                    purchase_order_id,
                    supplier_id,
                    status,
                    previous_status,
                    action,
                    notes,
                    changed_by,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                po_id,
                supplier_id,
                "Submitted",
                "Accepted",
                "QUOTATION_SUBMITTED",
                f"Quotation {quotation_num} submitted with {len(validated_items)} item(s) by {supplier_name}",
                username or supplier_name
            ))

        conn.commit()

        # Trigger Event C: New Quotation Submitted
        if initial_status == "Submitted" and po_id:
            try:
                from app.services.team3.notification_service import (
                    create_notification,
                    get_po_creator_user_id,
                    get_active_managers_and_owners
                )
                recipients = set(get_active_managers_and_owners())
                po_creator = get_po_creator_user_id(po_id)
                if po_creator:
                    recipients.add(po_creator)
                for r_uid in recipients:
                    create_notification(
                        user_id=r_uid,
                        title="New Quotation Submitted",
                        message=f"A new quotation has been submitted for Purchase Order #{po_id}.",
                        notification_type="Quotation Submitted",
                        priority="High",
                        reference_type="PurchaseOrder",
                        reference_id=po_id
                    )
            except Exception as notif_err:
                print(f"[NOTIFICATION WARNING] Failed to notify quotation submission: {notif_err}", flush=True)

        result = {
            "quotation_number": quotation_num,
            "purchase_order_id": po_id,
            "supplier_id": supplier_id,
            "status": initial_status,
            "items_count": len(created_quotations),
            "total_value": sum(item["total_amount"] for item in created_quotations),
            "items": created_quotations,
            "quotation_id": created_quotations[0]["quotation_id"]
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


def update_draft_quotation(quotation_id, data, user_id, role):
    """
    Update a draft quotation.
    Only quotations with status == 'Draft' can be edited.
    Suppliers can only edit their own quotations.
    """
    try:
        quotation_id = int(quotation_id)
    except (ValueError, TypeError):
        return None, "Invalid quotation_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT quotation_id, supplier_id, status, quoted_price, quantity, notes, valid_until
            FROM "SupplierQuotations"
            WHERE quotation_id = %s
        """, (quotation_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Quotation not found"

        supplier_id = row[1]
        status = row[2] or "Pending"

        # Supplier isolation check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                conn.rollback()
                return None, "Access denied. You can only edit your own quotations."

        # Status check
        if status.lower() != 'draft':
            conn.rollback()
            return None, f"Only Draft quotations can be edited. Current status is '{status}'."

        # Prepare updates
        qty = data.get("quantity", row[4])
        try:
            qty = int(qty)
            if qty <= 0:
                conn.rollback()
                return None, "quantity must be greater than zero"
        except (ValueError, TypeError):
            conn.rollback()
            return None, "quantity must be a valid integer"

        price = data.get("quoted_price", row[3])
        try:
            price = Decimal(str(price))
            if price < 0:
                conn.rollback()
                return None, "quoted_price cannot be negative"
        except Exception:
            conn.rollback()
            return None, "quoted_price must be a valid number"

        notes = data.get("notes", row[5])
        valid_until = data.get("valid_until", row[6])
        new_total = Decimal(str(round(qty * float(price), 2)))

        cursor.execute("""
            UPDATE "SupplierQuotations"
            SET quantity = %s,
                quoted_price = %s,
                total_amount = %s,
                notes = %s,
                valid_until = %s
            WHERE quotation_id = %s
        """, (qty, price, new_total, notes, valid_until if valid_until else None, quotation_id))

        conn.commit()
        return {"quotation_id": quotation_id, "quantity": qty, "quoted_price": float(price), "total_amount": float(new_total), "status": status}, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def submit_quotation(quotation_id, user_id, role, username):
    """
    Submit a Draft quotation to Manager/Owner.
    Changes status from 'Draft' to 'Submitted'.
    Logs event into OrderStatusHistory.
    """
    try:
        quotation_id = int(quotation_id)
    except (ValueError, TypeError):
        return None, "Invalid quotation_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT q.quotation_id, q.supplier_id, q.status, q.purchase_order_id, q.quotation_number, s.supplier_name
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            WHERE q.quotation_id = %s
        """, (quotation_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Quotation not found"

        supplier_id = row[1]
        status = row[2] or "Pending"
        po_id = row[3]
        q_num = row[4] or f"QT-2026-{quotation_id:04d}"
        s_name = row[5]

        # Supplier isolation check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != supplier_id:
                conn.rollback()
                return None, "Access denied. You can only submit your own quotations."

        if status.lower() != 'draft':
            conn.rollback()
            return None, f"Only Draft quotations can be submitted. Current status is '{status}'."

        cursor.execute("""
            UPDATE "SupplierQuotations"
            SET status = 'Submitted',
                submitted_at = NOW()
            WHERE quotation_id = %s
        """, (quotation_id,))

        if po_id:
            cursor.execute("""
                INSERT INTO "OrderStatusHistory" (
                    purchase_order_id,
                    supplier_id,
                    status,
                    previous_status,
                    action,
                    notes,
                    changed_by,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                po_id,
                supplier_id,
                "Submitted",
                "Draft",
                "QUOTATION_SUBMITTED",
                f"Quotation {q_num} submitted by {s_name}",
                username or s_name
            ))

        conn.commit()

        # Trigger Event C: New Quotation Submitted
        if po_id:
            try:
                from app.services.team3.notification_service import (
                    create_notification,
                    get_po_creator_user_id,
                    get_active_managers_and_owners
                )
                recipients = set(get_active_managers_and_owners())
                po_creator = get_po_creator_user_id(po_id)
                if po_creator:
                    recipients.add(po_creator)
                for r_uid in recipients:
                    create_notification(
                        user_id=r_uid,
                        title="New Quotation Submitted",
                        message=f"A new quotation has been submitted for Purchase Order #{po_id}.",
                        notification_type="Quotation Submitted",
                        priority="High",
                        reference_type="PurchaseOrder",
                        reference_id=po_id
                    )
            except Exception as notif_err:
                print(f"[NOTIFICATION WARNING] Failed to notify quotation submission: {notif_err}", flush=True)

        return {"quotation_id": quotation_id, "status": "Submitted", "quotation_number": q_num}, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def approve_quotation(quotation_id, user_id, role, username):
    """
    Approve a submitted quotation.
    Owner/Manager only.
    - Marks selected quotation as 'Approved'.
    - Marks competing quotations for the same PO (and product) as 'Rejected'.
    - Enforces at most one approved quotation per PO/product.
    - Logs transition to OrderStatusHistory.
    """
    if role not in ('Owner', 'Manager'):
        return None, "Only Owner or Manager can approve quotations"

    try:
        quotation_id = int(quotation_id)
    except (ValueError, TypeError):
        return None, "Invalid quotation_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT q.quotation_id, q.purchase_order_id, q.supplier_id, q.product_id, q.status, q.quotation_number, s.supplier_name
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            WHERE q.quotation_id = %s
        """, (quotation_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Quotation not found"

        po_id = row[1]
        supplier_id = row[2]
        product_id = row[3]
        status = row[4] or "Pending"
        q_num = row[5] or f"QT-2026-{quotation_id:04d}"
        supplier_name = row[6]

        if status in ('Approved', 'Accepted'):
            conn.rollback()
            return None, "Quotation is already approved"

        if status.lower() == 'draft':
            conn.rollback()
            return None, "Draft quotations cannot be approved. Supplier must submit the quotation first."

        if status.lower() == 'rejected':
            conn.rollback()
            return None, "Rejected quotations cannot be approved"

        # Check if another quotation for this PO and product is already approved
        if po_id:
            cursor.execute("""
                SELECT quotation_id, quotation_number FROM "SupplierQuotations"
                WHERE purchase_order_id = %s AND product_id = %s AND status IN ('Approved', 'Accepted') AND quotation_id != %s
            """, (po_id, product_id, quotation_id))
            already_approved = cursor.fetchone()
            if already_approved:
                conn.rollback()
                return None, f"Another quotation (#{already_approved[0]}) for this Purchase Order has already been approved"

        # 1. Approve selected quotation
        cursor.execute("""
            UPDATE "SupplierQuotations"
            SET status = 'Approved',
                approved_at = NOW(),
                approved_by = %s
            WHERE quotation_id = %s
        """, (int(user_id), quotation_id))

        # 2. Find and reject competing quotations for the same PO and product
        competing_count = 0
        competing_suppliers = []
        if po_id:
            cursor.execute("""
                SELECT DISTINCT supplier_id FROM "SupplierQuotations"
                WHERE purchase_order_id = %s 
                  AND product_id = %s 
                  AND quotation_id != %s 
                  AND status IN ('Submitted', 'Pending', 'Under Review')
            """, (po_id, product_id, quotation_id))
            competing_suppliers = [r[0] for r in cursor.fetchall()]

            cursor.execute("""
                UPDATE "SupplierQuotations"
                SET status = 'Rejected',
                    rejection_reason = %s
                WHERE purchase_order_id = %s 
                  AND product_id = %s 
                  AND quotation_id != %s 
                  AND status IN ('Submitted', 'Pending', 'Under Review')
            """, (f"Not selected. Quotation {q_num} was selected and approved.", po_id, product_id, quotation_id))
            competing_count = cursor.rowcount

        # 3. Log event into OrderStatusHistory
        if po_id:
            cursor.execute("""
                INSERT INTO "OrderStatusHistory" (
                    purchase_order_id,
                    supplier_id,
                    status,
                    previous_status,
                    action,
                    notes,
                    changed_by,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                po_id,
                supplier_id,
                "Approved",
                status,
                "QUOTATION_APPROVED",
                f"Quotation {q_num} from {supplier_name} approved by {username}. {competing_count} competing quote(s) rejected.",
                username
            ))

        conn.commit()

        # Trigger Event D: Quotation Approved -> notify approved supplier
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_supplier_user_id
            )
            sup_user_id = get_supplier_user_id(supplier_id)
            if sup_user_id:
                create_notification(
                    user_id=sup_user_id,
                    title="Quotation Approved",
                    message=f"Your quotation for Purchase Order #{po_id} has been approved." if po_id else "Your quotation has been approved.",
                    notification_type="Quotation Approved",
                    priority="High",
                    reference_type="PurchaseOrder",
                    reference_id=po_id
                )
            # Trigger Event E: Notify competing suppliers of rejection
            for comp_sup_id in competing_suppliers:
                c_user_id = get_supplier_user_id(comp_sup_id)
                if c_user_id and c_user_id != sup_user_id:
                    create_notification(
                        user_id=c_user_id,
                        title="Quotation Rejected",
                        message=f"Your quotation for Purchase Order #{po_id} has been rejected." if po_id else "Your quotation has been rejected.",
                        notification_type="Quotation Rejected",
                        priority="High",
                        reference_type="PurchaseOrder",
                        reference_id=po_id
                    )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to send quotation approval/rejection notifications: {notif_err}", flush=True)

        return {
            "quotation_id": quotation_id,
            "quotation_number": q_num,
            "status": "Approved",
            "competing_rejected": competing_count,
            "message": f"Quotation {q_num} approved successfully"
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


def reject_quotation(quotation_id, rejection_reason, user_id, role, username):
    """
    Reject a quotation explicitly.
    Owner/Manager only.
    """
    if role not in ('Owner', 'Manager'):
        return None, "Only Owner or Manager can reject quotations"

    try:
        quotation_id = int(quotation_id)
    except (ValueError, TypeError):
        return None, "Invalid quotation_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        cursor.execute("""
            SELECT q.quotation_id, q.purchase_order_id, q.supplier_id, q.status, q.quotation_number, s.supplier_name
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            WHERE q.quotation_id = %s
        """, (quotation_id,))
        row = cursor.fetchone()

        if not row:
            conn.rollback()
            return None, "Quotation not found"

        po_id = row[1]
        supplier_id = row[2]
        status = row[3] or "Pending"
        q_num = row[4] or f"QT-2026-{quotation_id:04d}"
        s_name = row[5]

        if status in ('Approved', 'Accepted'):
            conn.rollback()
            return None, "Cannot reject an already Approved quotation"

        reason = rejection_reason or "Rejected by manager"

        cursor.execute("""
            UPDATE "SupplierQuotations"
            SET status = 'Rejected',
                rejection_reason = %s
            WHERE quotation_id = %s
        """, (reason, quotation_id))

        if po_id:
            cursor.execute("""
                INSERT INTO "OrderStatusHistory" (
                    purchase_order_id,
                    supplier_id,
                    status,
                    previous_status,
                    action,
                    notes,
                    changed_by,
                    created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                po_id,
                supplier_id,
                "Rejected",
                status,
                "QUOTATION_REJECTED",
                f"Quotation {q_num} rejected: {reason}",
                username
            ))

        conn.commit()

        # Trigger Event E: Quotation Rejected -> notify supplier
        try:
            from app.services.team3.notification_service import (
                create_notification,
                get_supplier_user_id
            )
            sup_user_id = get_supplier_user_id(supplier_id)
            if sup_user_id:
                msg = f"Your quotation for Purchase Order #{po_id} has been rejected. Reason: {reason}" if reason else f"Your quotation for Purchase Order #{po_id} has been rejected."
                create_notification(
                    user_id=sup_user_id,
                    title="Quotation Rejected",
                    message=msg,
                    notification_type="Quotation Rejected",
                    priority="High",
                    reference_type="PurchaseOrder",
                    reference_id=po_id
                )
        except Exception as notif_err:
            print(f"[NOTIFICATION WARNING] Failed to notify quotation rejection: {notif_err}", flush=True)

        return {"quotation_id": quotation_id, "status": "Rejected", "rejection_reason": reason}, None

    except Exception as e:
        if conn:
            conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def compare_quotations_for_po(purchase_order_id, user_id=None, role=None):
    """
    Side-by-side comparison of all quotations submitted for a Purchase Order.
    Owner/Manager view to evaluate competing supplier offers.
    """
    try:
        po_id = int(purchase_order_id)
    except (ValueError, TypeError):
        return None, "Invalid purchase_order_id"

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch Purchase Order Info
        cursor.execute("""
            SELECT po.purchase_order_id, po.order_date, po.expected_delivery, po.total_amount, po.status
            FROM "PurchaseOrders" po
            WHERE po.purchase_order_id = %s
        """, (po_id,))
        po_row = cursor.fetchone()
        if not po_row:
            return None, "Purchase order not found"

        # 2. Fetch original PO items
        cursor.execute("""
            SELECT poi.product_id, p.product_name, p.sku, poi.quantity, poi.unit_price, poi.subtotal
            FROM "PurchaseOrderItems" poi
            JOIN "Products" p ON poi.product_id = p.product_id
            WHERE poi.purchase_order_id = %s
        """, (po_id,))
        po_items = []
        for r in cursor.fetchall():
            po_items.append({
                "product_id": r[0],
                "product_name": r[1],
                "sku": r[2],
                "required_quantity": r[3],
                "target_unit_price": float(r[4]),
                "target_subtotal": float(r[5])
            })

        # 3. Fetch all quotations for this PO
        cursor.execute("""
            SELECT 
                q.quotation_id,
                q.quotation_number,
                q.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email,
                q.product_id,
                p.product_name,
                q.quantity,
                q.quoted_price,
                COALESCE(q.total_amount, (q.quantity * q.quoted_price)) AS total_amount,
                q.quotation_date,
                q.valid_until,
                q.status,
                q.notes,
                q.submitted_at
            FROM "SupplierQuotations" q
            JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
            JOIN "Products" p ON q.product_id = p.product_id
            WHERE q.purchase_order_id = %s
            ORDER BY q.product_id, q.quoted_price ASC
        """, (po_id,))

        quotes = []
        for r in cursor.fetchall():
            qid = r[0]
            quotes.append({
                "quotation_id": qid,
                "quotation_number": r[1] or f"QT-2026-{qid:04d}",
                "supplier_id": r[2],
                "supplier_name": r[3],
                "contact_person": r[4] or "",
                "supplier_email": r[5] or "",
                "product_id": r[6],
                "product_name": r[7],
                "offered_quantity": r[8],
                "quoted_price": float(r[9]),
                "total_amount": float(r[10]),
                "quotation_date": r[11].isoformat() if r[11] else None,
                "valid_until": r[12].isoformat() if r[12] else None,
                "status": r[13],
                "notes": r[14] or "",
                "submitted_at": r[15].isoformat() if r[15] else None
            })

        comparison_data = {
            "purchase_order": {
                "purchase_order_id": po_row[0],
                "order_date": po_row[1].isoformat() if po_row[1] else None,
                "expected_delivery": po_row[2].isoformat() if po_row[2] else None,
                "total_amount": float(po_row[3]),
                "status": po_row[4],
                "items": po_items
            },
            "quotations": quotes,
            "total_quotations": len(quotes)
        }
        return comparison_data, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
