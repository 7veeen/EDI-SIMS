from datetime import date, datetime
from decimal import Decimal
from app.extensions import get_db_connection


def get_supplier_id_for_user(user_id):
    """
    Helper to look up the supplier_id and supplier_name linked to a user_id.
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


def get_purchase_orders(user_id=None, role=None, search=None, status=None, supplier_id_filter=None):
    """
    List purchase orders with role-based access control.
    Suppliers strictly see only their own assigned purchase orders.
    Owners/Managers see all purchase orders, with optional filtering.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Supplier Isolation Check
        supplier_id = None
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row:
                # User is a Supplier but has no linked supplier profile
                return [], {
                    "total_orders": 0,
                    "pending": 0,
                    "accepted": 0,
                    "rejected": 0,
                    "total_value": 0.0
                }, None
            supplier_id = s_row[0]
        elif supplier_id_filter:
            try:
                supplier_id = int(supplier_id_filter)
            except (ValueError, TypeError):
                supplier_id = None

        query = """
            SELECT 
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                po.ordered_by,
                u.username AS ordered_by_username,
                po.order_date,
                po.expected_delivery,
                po.total_amount,
                po.status,
                po.supplier_response,
                po.supplier_response_date,
                po.rejection_reason,
                COUNT(poi.purchase_order_item_id) AS total_items
            FROM "PurchaseOrders" po
            JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
            JOIN "Users" u ON po.ordered_by = u.user_id
            LEFT JOIN "PurchaseOrderItems" poi ON po.purchase_order_id = poi.purchase_order_id
            WHERE 1=1
        """
        params = []

        if supplier_id:
            query += " AND po.supplier_id = %s"
            params.append(supplier_id)

        if status and status.strip():
            query += " AND po.status = %s"
            params.append(status.strip())

        if search and search.strip():
            search_param = f"%{search.strip()}%"
            query += """
                AND (
                    po.purchase_order_id::text ILIKE %s
                    OR s.supplier_name ILIKE %s
                    OR u.username ILIKE %s
                )
            """
            params.extend([search_param, search_param, search_param])

        query += """
            GROUP BY 
                po.purchase_order_id,
                s.supplier_name,
                s.contact_person,
                s.email,
                s.phone,
                u.username
            ORDER BY po.purchase_order_id DESC
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        orders = []
        total_value = Decimal('0.00')
        pending_count = 0
        accepted_count = 0
        rejected_count = 0

        for r in rows:
            amt = float(r[10]) if r[10] is not None else 0.0
            order_status = r[11]

            total_value += Decimal(str(amt))
            if order_status == 'Pending':
                pending_count += 1
            elif order_status in ['Accepted', 'Delivered']:
                accepted_count += 1
            elif order_status == 'Rejected':
                rejected_count += 1

            orders.append({
                "purchase_order_id": r[0],
                "po_number": f"PO-{r[0]:04d}",
                "supplier_id": r[1],
                "supplier_name": r[2],
                "contact_person": r[3] or "",
                "supplier_email": r[4] or "",
                "supplier_phone": r[5] or "",
                "ordered_by": r[6],
                "ordered_by_username": r[7],
                "order_date": r[8].isoformat() if r[8] else None,
                "expected_delivery": r[9].isoformat() if r[9] else None,
                "total_amount": amt,
                "status": order_status,
                "supplier_response": r[12] or "Pending",
                "supplier_response_date": r[13].isoformat() if r[13] else None,
                "rejection_reason": r[14] or "",
                "total_items": r[15]
            })

        stats = {
            "total_orders": len(orders),
            "pending": pending_count,
            "accepted": accepted_count,
            "rejected": rejected_count,
            "total_value": float(total_value)
        }

        return orders, stats, None

    except Exception as e:
        return None, None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def get_purchase_order_by_id(purchase_order_id, user_id=None, role=None):
    """
    Get full purchase order details, including line items and status history.
    Enforces supplier isolation: Supplier can only view POs assigned to their supplier_id.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch PO Header
        query = """
            SELECT 
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                s.contact_person,
                s.email AS supplier_email,
                s.phone AS supplier_phone,
                po.ordered_by,
                u.username AS ordered_by_username,
                po.order_date,
                po.expected_delivery,
                po.total_amount,
                po.status,
                po.supplier_response,
                po.supplier_response_date,
                po.rejection_reason
            FROM "PurchaseOrders" po
            JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
            JOIN "Users" u ON po.ordered_by = u.user_id
            WHERE po.purchase_order_id = %s
        """
        cursor.execute(query, (purchase_order_id,))
        row = cursor.fetchone()

        if not row:
            return None, "Purchase order not found"

        po_supplier_id = row[1]

        # Supplier Isolation Check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != po_supplier_id:
                return None, "Access denied"

        # Fetch Line Items
        items_query = """
            SELECT 
                poi.purchase_order_item_id,
                poi.purchase_order_id,
                poi.product_id,
                p.product_name,
                p.sku,
                poi.quantity,
                poi.unit_price,
                poi.subtotal
            FROM "PurchaseOrderItems" poi
            JOIN "Products" p ON poi.product_id = p.product_id
            WHERE poi.purchase_order_id = %s
            ORDER BY poi.purchase_order_item_id ASC
        """
        cursor.execute(items_query, (purchase_order_id,))
        item_rows = cursor.fetchall()

        items = []
        for ir in item_rows:
            items.append({
                "purchase_order_item_id": ir[0],
                "purchase_order_id": ir[1],
                "product_id": ir[2],
                "product_name": ir[3],
                "sku": ir[4],
                "quantity": ir[5],
                "unit_price": float(ir[6]),
                "subtotal": float(ir[7])
            })

        # Fetch Order Status History
        history_query = """
            SELECT 
                h.history_id,
                h.status,
                h.previous_status,
                h.action,
                h.location,
                h.notes,
                h.changed_by,
                h.created_at
            FROM "OrderStatusHistory" h
            WHERE h.purchase_order_id = %s
            ORDER BY h.history_id ASC
        """
        cursor.execute(history_query, (purchase_order_id,))
        history_rows = cursor.fetchall()

        history = []
        for hr in history_rows:
            history.append({
                "history_id": hr[0],
                "status": hr[1],
                "previous_status": hr[2],
                "action": hr[3],
                "location": hr[4] or "",
                "notes": hr[5] or "",
                "changed_by": hr[6] or "",
                "created_at": hr[7].isoformat() if hr[7] else None
            })

        order_data = {
            "purchase_order_id": row[0],
            "po_number": f"PO-{row[0]:04d}",
            "supplier_id": row[1],
            "supplier_name": row[2],
            "contact_person": row[3] or "",
            "supplier_email": row[4] or "",
            "supplier_phone": row[5] or "",
            "ordered_by": row[6],
            "ordered_by_username": row[7],
            "order_date": row[8].isoformat() if row[8] else None,
            "expected_delivery": row[9].isoformat() if row[9] else None,
            "total_amount": float(row[10]),
            "status": row[11],
            "supplier_response": row[12] or "Pending",
            "supplier_response_date": row[13].isoformat() if row[13] else None,
            "rejection_reason": row[14] or "",
            "items": items,
            "status_history": history
        }

        return order_data, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def create_purchase_order(data, ordered_by_user_id, username):
    """
    Create a new purchase order with multiple items atomically.
    Validates supplier, products, quantities, prices, and calculates line subtotals and total.
    Inserts initial status into OrderStatusHistory within the same transaction.
    """
    if not data or not isinstance(data, dict):
        return None, "Request body is required"

    supplier_id = data.get("supplier_id")
    if not supplier_id:
        return None, "supplier_id is required"

    try:
        supplier_id = int(supplier_id)
    except (ValueError, TypeError):
        return None, "supplier_id must be a valid integer"

    items = data.get("items")
    if not items or not isinstance(items, list) or len(items) == 0:
        return None, "Purchase order must contain at least one item in 'items'"

    expected_delivery = data.get("expected_delivery")
    if expected_delivery and str(expected_delivery).strip():
        expected_delivery = str(expected_delivery).strip()
    else:
        expected_delivery = None

    order_date = data.get("order_date")
    if order_date and str(order_date).strip():
        order_date = str(order_date).strip()
    else:
        order_date = date.today().isoformat()

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Validate Supplier exists and is Active
        cursor.execute('SELECT supplier_id, supplier_name, status FROM "Suppliers" WHERE supplier_id = %s', (supplier_id,))
        supplier_row = cursor.fetchone()
        if not supplier_row:
            return None, "Supplier does not exist"
        if supplier_row[2] != 'Active':
            return None, f"Supplier '{supplier_row[1]}' is inactive and cannot receive purchase orders"

        supplier_name = supplier_row[1]

        # 2. Validate all products and calculate line subtotals
        validated_items = []
        computed_total = Decimal('0.00')

        for idx, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                return None, f"Item #{idx} is invalid"

            prod_id = item.get("product_id")
            if not prod_id:
                return None, f"Item #{idx}: product_id is required"

            try:
                prod_id = int(prod_id)
            except (ValueError, TypeError):
                return None, f"Item #{idx}: product_id must be an integer"

            qty = item.get("quantity")
            if qty is None:
                return None, f"Item #{idx}: quantity is required"

            try:
                qty = int(qty)
            except (ValueError, TypeError):
                return None, f"Item #{idx}: quantity must be an integer"

            if qty <= 0:
                return None, f"Item #{idx}: quantity must be greater than zero"

            # Check product existence & status
            cursor.execute('SELECT product_id, product_name, selling_price, status FROM "Products" WHERE product_id = %s', (prod_id,))
            prod_row = cursor.fetchone()
            if not prod_row:
                return None, f"Item #{idx}: Product with ID {prod_id} does not exist"
            if prod_row[3] != 'Active':
                return None, f"Item #{idx}: Product '{prod_row[1]}' is inactive and cannot be ordered"

            # Unit price: user-specified or database selling_price
            unit_price_val = item.get("unit_price")
            if unit_price_val is not None and str(unit_price_val).strip() != "":
                try:
                    unit_price = Decimal(str(unit_price_val))
                except Exception:
                    return None, f"Item #{idx}: unit_price is invalid"
                if unit_price < 0:
                    return None, f"Item #{idx}: unit_price cannot be negative"
            else:
                unit_price = Decimal(str(prod_row[2]))

            subtotal = Decimal(str(round(qty * float(unit_price), 2)))
            computed_total += subtotal

            validated_items.append({
                "product_id": prod_id,
                "product_name": prod_row[1],
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal
            })

        # 3. Insert Purchase Order Header
        cursor.execute("""
            INSERT INTO "PurchaseOrders" (
                supplier_id,
                ordered_by,
                order_date,
                expected_delivery,
                total_amount,
                status,
                supplier_response
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING purchase_order_id, order_date, expected_delivery, total_amount, status, supplier_response
        """, (
            supplier_id,
            int(ordered_by_user_id),
            order_date,
            expected_delivery,
            computed_total,
            'Pending',
            'Pending'
        ))

        po_row = cursor.fetchone()
        new_po_id = po_row[0]

        # 4. Insert Purchase Order Line Items
        created_items = []
        for vi in validated_items:
            cursor.execute("""
                INSERT INTO "PurchaseOrderItems" (
                    purchase_order_id,
                    product_id,
                    quantity,
                    unit_price,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING purchase_order_item_id
            """, (
                new_po_id,
                vi["product_id"],
                vi["quantity"],
                vi["unit_price"],
                vi["subtotal"]
            ))
            item_id = cursor.fetchone()[0]
            created_items.append({
                "purchase_order_item_id": item_id,
                "product_id": vi["product_id"],
                "product_name": vi["product_name"],
                "quantity": vi["quantity"],
                "unit_price": float(vi["unit_price"]),
                "subtotal": float(vi["subtotal"])
            })

        # 5. Insert initial OrderStatusHistory entry
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
            new_po_id,
            supplier_id,
            'Pending',
            None,
            'Order Created',
            f'Purchase order created with {len(created_items)} items for {supplier_name}',
            username or 'Manager'
        ))

        # Atomic commit
        conn.commit()

        result = {
            "purchase_order_id": new_po_id,
            "po_number": f"PO-{new_po_id:04d}",
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "ordered_by": int(ordered_by_user_id),
            "ordered_by_username": username,
            "order_date": po_row[1].isoformat() if po_row[1] else str(order_date),
            "expected_delivery": po_row[2].isoformat() if po_row[2] else None,
            "total_amount": float(computed_total),
            "status": po_row[4],
            "supplier_response": po_row[5],
            "items": created_items
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


def respond_to_purchase_order(purchase_order_id, response_data, user_id=None, role=None, username=None):
    """
    Supplier accepts or rejects a purchase order.
    Enforces that:
    1. Authenticated user is the supplier assigned to this PO.
    2. PO is currently in 'Pending' state.
    3. If rejected, a rejection_reason is provided.
    4. OrderStatusHistory is updated with the decision.
    """
    if not response_data or not isinstance(response_data, dict):
        return None, "Request body is required"

    action = response_data.get("response") or response_data.get("status") or response_data.get("action")
    if not action or not str(action).strip():
        return None, "Response action is required ('Accepted' or 'Rejected')"

    action = str(action).strip().capitalize()
    if action not in ['Accepted', 'Rejected']:
        return None, "Response must be either 'Accepted' or 'Rejected'"

    rejection_reason = response_data.get("rejection_reason")
    if action == 'Rejected':
        if not rejection_reason or not str(rejection_reason).strip():
            return None, "rejection_reason is required when rejecting a purchase order"
        rejection_reason = str(rejection_reason).strip()
    else:
        rejection_reason = None

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch PO to verify existence and ownership
        cursor.execute("""
            SELECT po.purchase_order_id, po.supplier_id, po.status, po.supplier_response, s.supplier_name
            FROM "PurchaseOrders" po
            JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
            WHERE po.purchase_order_id = %s
        """, (purchase_order_id,))
        po_row = cursor.fetchone()

        if not po_row:
            return None, "Purchase order not found"

        po_id = po_row[0]
        po_supplier_id = po_row[1]
        current_status = po_row[2]
        current_response = po_row[3]
        supplier_name = po_row[4]

        # Supplier isolation check
        if role == 'Supplier':
            cursor.execute('SELECT supplier_id FROM "Suppliers" WHERE user_id = %s', (int(user_id),))
            s_row = cursor.fetchone()
            if not s_row or s_row[0] != po_supplier_id:
                return None, "Access denied"

        # Check if PO is in a response-eligible state ('Pending')
        if current_status not in ['Pending', 'Created'] or current_response not in ['Pending', 'Created']:
            return None, f"Purchase order has already been {current_response.lower()} and cannot be changed"

        # Update PurchaseOrders record
        cursor.execute("""
            UPDATE "PurchaseOrders"
            SET 
                status = %s,
                supplier_response = %s,
                supplier_response_date = NOW(),
                rejection_reason = %s
            WHERE purchase_order_id = %s
            RETURNING purchase_order_id, status, supplier_response, supplier_response_date, rejection_reason
        """, (
            action,
            action,
            rejection_reason,
            po_id
        ))
        updated_row = cursor.fetchone()

        # Insert entry into OrderStatusHistory
        notes_text = rejection_reason if action == 'Rejected' else 'Order accepted by supplier and scheduled for fulfillment'
        actor_name = supplier_name if role == 'Supplier' else (username or 'Supplier')

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
            po_supplier_id,
            action,
            current_status,
            f"Order {action}",
            notes_text,
            actor_name
        ))

        conn.commit()

        result = {
            "purchase_order_id": updated_row[0],
            "po_number": f"PO-{updated_row[0]:04d}",
            "status": updated_row[1],
            "supplier_response": updated_row[2],
            "supplier_response_date": updated_row[3].isoformat() if updated_row[3] else None,
            "rejection_reason": updated_row[4],
            "message": f"Purchase order successfully {action.lower()}"
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
