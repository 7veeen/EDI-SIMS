from app.extensions import get_db_connection


def get_employee_dashboard(user_id=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Total number of products
        cursor.execute('SELECT COUNT(*) FROM "Products"')
        total_products = cursor.fetchone()[0]

        # Total available stock
        cursor.execute('SELECT COALESCE(SUM(quantity_available), 0) FROM "Inventory"')
        total_stock = cursor.fetchone()[0]

        # Stock in
        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_type = 'STOCK_IN'
        ''')
        stock_in = cursor.fetchone()[0]

        # Stock out
        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_type = 'STOCK_OUT'
        ''')
        stock_out = cursor.fetchone()[0]

        # Low-stock products using dynamic reorder level
        cursor.execute('''
            SELECT
                p.product_id,
                p.product_name,
                i.quantity_available
            FROM "Products" p
            JOIN "Inventory" i
                ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
            ORDER BY i.quantity_available ASC
        ''')
        low_stock_rows = cursor.fetchall()

        low_stock_products = []

        for row in low_stock_rows:
            low_stock_products.append({
                "product_id": row[0],
                "product_name": row[1],
                "quantity_available": row[2]
            })

        tasks = []
        if user_id:
            cursor.execute('''
                SELECT notification_id, title, message, created_at, is_read
                FROM "Notifications"
                WHERE user_id = %s AND is_read = false
                ORDER BY created_at DESC
                LIMIT 10
            ''', (user_id,))
            notif_rows = cursor.fetchall()
            for row in notif_rows:
                tasks.append({
                    "notification_id": row[0],
                    "title": row[1],
                    "message": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "is_read": row[4]
                })

        return {
            "total_products": total_products,
            "total_stock": total_stock,
            "stock_in": stock_in,
            "stock_out": stock_out,
            "low_stock_products": low_stock_products,
            "tasks": tasks
        }

    finally:
        cursor.close()
        conn.close()


def get_supplier_dashboard(user_id=None):
    """
    Get live database-driven dashboard metrics for the authenticated Supplier.
    Strictly isolated: never aggregates data belonging to other suppliers.
    """
    if not user_id:
        return None, "Authenticated user identity required."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Resolve supplier_id from authenticated JWT user_id
        cursor.execute("""
            SELECT supplier_id, supplier_name, contact_person, phone, email, status
            FROM "Suppliers"
            WHERE user_id = %s
        """, (int(user_id),))
        sup = cursor.fetchone()

        if not sup:
            return None, "Supplier profile not found for authenticated user."

        supplier_id = sup[0]
        supplier_name = sup[1]
        contact_person = sup[2] or ""
        phone = sup[3] or ""
        email = sup[4] or ""
        status = sup[5] or "Active"

        # 1. Open Requests (from StockRequests)
        cursor.execute("""
            SELECT COUNT(*)
            FROM "StockRequests"
            WHERE supplier_id = %s AND status IN ('Pending', 'Open')
        """, (supplier_id,))
        open_requests = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM "StockRequests"
            WHERE supplier_id = %s
        """, (supplier_id,))
        total_requests = cursor.fetchone()[0]

        # 2. Pending Quotations (from SupplierQuotations)
        cursor.execute("""
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE supplier_id = %s AND status IN ('Pending', 'Submitted', 'Under Review')
        """, (supplier_id,))
        pending_quotations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE supplier_id = %s AND status IN ('Approved', 'Accepted')
        """, (supplier_id,))
        approved_quotations = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE supplier_id = %s
        """, (supplier_id,))
        total_quotations = cursor.fetchone()[0]

        # 3. Active POs (Purchase Orders belonging to this supplier not Completed, Rejected, or Cancelled)
        cursor.execute("""
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE supplier_id = %s AND status NOT IN ('Completed', 'Rejected', 'Cancelled')
        """, (supplier_id,))
        active_pos = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
        """, (supplier_id,))
        total_purchase_orders = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0)
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
        """, (supplier_id,))
        total_order_value = float(cursor.fetchone()[0])

        # 4. Pending Payments
        # Note: Database does not have a Payments/Invoices table yet. We explicitly report this.
        pending_payments = None
        has_payment_module = False

        # 5. On-time Delivery Rate
        # Calculate from actual delivered shipments where expected_delivery is set
        cursor.execute("""
            SELECT expected_delivery, delivered_at
            FROM "Shipments"
            WHERE supplier_id = %s AND status = 'Delivered' AND delivered_at IS NOT NULL
        """, (supplier_id,))
        shipment_rows = cursor.fetchall()

        total_deliveries = len(shipment_rows)
        on_time_count = 0
        for s_row in shipment_rows:
            exp_date = s_row[0]
            deliv_time = s_row[1]
            if exp_date and deliv_time:
                # If delivered on or before the expected delivery date
                if deliv_time.date() <= exp_date:
                    on_time_count += 1
            else:
                on_time_count += 1  # Count as on-time if no target date was breached

        on_time_delivery_rate = round((on_time_count / total_deliveries) * 100, 1) if total_deliveries > 0 else None

        # 6. Quotation Acceptance Rate
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status IN ('Approved', 'Accepted')) AS approved,
                COUNT(*) FILTER (WHERE status IN ('Approved', 'Accepted', 'Rejected')) AS resolved,
                COUNT(*) AS total
            FROM "SupplierQuotations"
            WHERE supplier_id = %s
        """, (supplier_id,))
        q_stats = cursor.fetchone()
        quotation_approved = q_stats[0] or 0
        quotation_resolved = q_stats[1] or 0
        quotation_acceptance_rate = round((quotation_approved / quotation_resolved) * 100, 1) if quotation_resolved > 0 else (
            100.0 if quotation_approved > 0 else None
        )

        # 7. Order Acceptance Rate
        cursor.execute("""
            SELECT
                COUNT(*) FILTER (WHERE supplier_response = 'Accepted') AS accepted,
                COUNT(*) FILTER (WHERE supplier_response IN ('Accepted', 'Rejected')) AS responded,
                COUNT(*) AS total
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
        """, (supplier_id,))
        po_stats = cursor.fetchone()
        po_accepted = po_stats[0] or 0
        po_responded = po_stats[1] or 0
        order_acceptance_rate = round((po_accepted / po_responded) * 100, 1) if po_responded > 0 else (
            100.0 if po_accepted > 0 else None
        )

        # 8. Profile Completion Rate
        profile_fields = [supplier_name, contact_person, phone, email, status]
        filled_count = sum(1 for f in profile_fields if f and str(f).strip())
        profile_completion = int(round((filled_count / len(profile_fields)) * 100))

        # Recent pending stock requests for actionable dashboard list
        cursor.execute("""
            SELECT
                sr.stock_request_id,
                sr.request_number,
                sr.priority,
                sr.required_date,
                sr.created_at,
                COALESCE(SUM(sri.requested_quantity), 0) AS total_qty,
                (
                    SELECT p.product_name
                    FROM "StockRequestItems" sri2
                    JOIN "Products" p ON sri2.product_id = p.product_id
                    WHERE sri2.stock_request_id = sr.stock_request_id
                    LIMIT 1
                ) AS primary_product
            FROM "StockRequests" sr
            LEFT JOIN "StockRequestItems" sri ON sr.stock_request_id = sri.stock_request_id
            WHERE sr.supplier_id = %s AND sr.status IN ('Pending', 'Open')
            GROUP BY sr.stock_request_id
            ORDER BY sr.created_at DESC
            LIMIT 5
        """, (supplier_id,))
        recent_req_rows = cursor.fetchall()

        recent_stock_requests = []
        for rr in recent_req_rows:
            recent_stock_requests.append({
                "stock_request_id": rr[0],
                "request_number": rr[1],
                "priority": rr[2] or "Medium",
                "required_date": rr[3].isoformat() if rr[3] else None,
                "created_at": rr[4].isoformat() if rr[4] else None,
                "total_quantity": int(rr[5]),
                "primary_product": rr[6] or "General Catalog"
            })

        # Recent purchase orders for this supplier
        cursor.execute("""
            SELECT
                purchase_order_id,
                order_date,
                expected_delivery,
                total_amount,
                status,
                supplier_response
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
            ORDER BY order_date DESC
            LIMIT 5
        """, (supplier_id,))
        recent_po_rows = cursor.fetchall()

        recent_orders = []
        for rpo in recent_po_rows:
            recent_orders.append({
                "purchase_order_id": rpo[0],
                "order_date": rpo[1].isoformat() if rpo[1] else None,
                "expected_delivery": rpo[2].isoformat() if rpo[2] else None,
                "total_amount": float(rpo[3]) if rpo[3] is not None else 0.0,
                "status": rpo[4],
                "supplier_response": rpo[5] or "Pending"
            })

        # 4. Pending Deliveries (Shipments not yet delivered or cancelled)
        cursor.execute("""
            SELECT COUNT(*)
            FROM "Shipments"
            WHERE supplier_id = %s AND status NOT IN ('Delivered', 'Cancelled')
        """, (supplier_id,))
        pending_deliveries = cursor.fetchone()[0]

        # Detailed shipment status counts (Step 5 statuses)
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM "Shipments"
            WHERE supplier_id = %s
            GROUP BY status
        """, (supplier_id,))
        raw_ship_counts = dict(cursor.fetchall())

        cursor.execute("""
            SELECT COUNT(*)
            FROM "Shipments"
            WHERE supplier_id = %s AND status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE
        """, (supplier_id,))
        delayed_deliveries = cursor.fetchone()[0]

        shipment_stats = {
            "ready_for_shipment": raw_ship_counts.get("Ready for Shipment", 0),
            "dispatched": raw_ship_counts.get("Dispatched", 0),
            "in_transit": raw_ship_counts.get("In Transit", 0),
            "delayed": delayed_deliveries,
            "delivered": raw_ship_counts.get("Delivered", 0),
            "total": sum(raw_ship_counts.values())
        }

        # 5. Actionable Items for "Needs Your Attention"
        attention_items = []

        # (a) Stock Requests awaiting response
        cursor.execute("""
            SELECT sr.stock_request_id, sr.request_number, sr.priority, sr.required_date, sr.created_at,
                   COALESCE((
                       SELECT p.product_name 
                       FROM "StockRequestItems" sri 
                       JOIN "Products" p ON sri.product_id = p.product_id 
                       WHERE sri.stock_request_id = sr.stock_request_id 
                       LIMIT 1
                   ), 'Restock Request') AS primary_product
            FROM "StockRequests" sr
            WHERE sr.supplier_id = %s AND sr.status IN ('Pending', 'Open')
            ORDER BY CASE WHEN sr.priority = 'Urgent' THEN 1 WHEN sr.priority = 'High' THEN 2 ELSE 3 END, sr.created_at DESC
            LIMIT 5
        """, (supplier_id,))
        for sr in cursor.fetchall():
            attention_items.append({
                "type": "stock_request",
                "id": sr[0],
                "reference": sr[1],
                "title": f"Stock Request {sr[1]} needs response",
                "description": f"Priority: {sr[2]} • Product: {sr[5]}",
                "date": sr[3].isoformat() if sr[3] else None,
                "status": "Pending",
                "priority": sr[2],
                "target_page": "stock-requests",
                "action_label": "Review"
            })

        # (b) Purchase Orders awaiting supplier response/acceptance
        cursor.execute("""
            SELECT po.purchase_order_id, po.order_date, po.total_amount, po.status, po.supplier_response
            FROM "PurchaseOrders" po
            WHERE po.supplier_id = %s AND (po.supplier_response = 'Pending' OR po.supplier_response IS NULL) AND po.status NOT IN ('Cancelled', 'Rejected', 'Delivered')
            ORDER BY po.order_date DESC
            LIMIT 5
        """, (supplier_id,))
        for po in cursor.fetchall():
            attention_items.append({
                "type": "purchase_order",
                "id": po[0],
                "reference": f"PO #{po[0]}",
                "title": f"PO #{po[0]} is awaiting your acceptance",
                "description": f"Order value: ₹{float(po[2]):,.2f} • Ordered: {po[1]}",
                "date": po[1].isoformat() if po[1] else None,
                "status": "Awaiting Acceptance",
                "priority": "High",
                "target_page": "purchase-orders",
                "action_label": "Review"
            })

        # (c) Delayed Shipments
        cursor.execute("""
            SELECT s.shipment_id, s.shipment_number, s.expected_delivery, s.status, s.purchase_order_id
            FROM "Shipments" s
            WHERE s.supplier_id = %s AND s.status NOT IN ('Delivered', 'Cancelled') AND s.expected_delivery < CURRENT_DATE
            ORDER BY s.expected_delivery ASC
            LIMIT 5
        """, (supplier_id,))
        for sh in cursor.fetchall():
            attention_items.append({
                "type": "delayed_shipment",
                "id": sh[0],
                "reference": sh[1],
                "title": f"Shipment {sh[1]} is delayed",
                "description": f"Expected on {sh[2]} for PO #{sh[4]}",
                "date": sh[2].isoformat() if sh[2] else None,
                "status": "Delayed",
                "priority": "Urgent",
                "target_page": "shipments",
                "action_label": "Track"
            })

        # 6. Recent Activity from OrderStatusHistory
        cursor.execute("""
            SELECT history_id, purchase_order_id, shipment_id, status, previous_status, action, notes, changed_by, created_at
            FROM "OrderStatusHistory"
            WHERE supplier_id = %s
            ORDER BY created_at DESC
            LIMIT 6
        """, (supplier_id,))
        history_rows = cursor.fetchall()
        recent_activity = []
        for h in history_rows:
            recent_activity.append({
                "history_id": h[0],
                "purchase_order_id": h[1],
                "shipment_id": h[2],
                "status": h[3],
                "previous_status": h[4],
                "action": h[5] or "UPDATE",
                "notes": h[6] or "",
                "changed_by": h[7] or "System",
                "created_at": h[8].isoformat() if h[8] else None
            })

        return {
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "supplier": {
                "supplier_id": supplier_id,
                "supplier_name": supplier_name
            },
            "open_requests": open_requests,
            "total_requests": total_requests,
            "pending_quotations": pending_quotations,
            "approved_quotations": approved_quotations,
            "total_quotations": total_quotations,
            "active_pos": active_pos,
            "total_purchase_orders": total_purchase_orders,
            "total_order_value": total_order_value,
            "pending_deliveries": pending_deliveries,
            "shipment_stats": shipment_stats,
            "attention_items": attention_items,
            "pending_payments": pending_payments,
            "has_payment_module": has_payment_module,
            "on_time_delivery_rate": on_time_delivery_rate,
            "quotation_acceptance_rate": quotation_acceptance_rate,
            "order_acceptance_rate": order_acceptance_rate,
            "profile_completion": profile_completion,
            "recent_stock_requests": recent_stock_requests,
            "recent_orders": recent_orders,
            "recent_activity": recent_activity
        }, None

    except Exception as e:
        return None, f"Database error: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def get_manager_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Active purchase orders (orders that are not Completed, Rejected, or Cancelled)
        cursor.execute('''
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE status NOT IN ('Completed', 'Rejected', 'Cancelled')
        ''')
        active_pos = cursor.fetchone()[0]

        # Pending purchase order value (value of purchase orders awaiting fulfillment)
        cursor.execute('''
            SELECT COALESCE(SUM(total_amount), 0)
            FROM "PurchaseOrders"
            WHERE status NOT IN ('Completed', 'Rejected', 'Cancelled')
        ''')
        pending_po_value = float(cursor.fetchone()[0])

        # Low-stock count using dynamic reorder level from Products
        cursor.execute('''
            SELECT COUNT(*)
            FROM "Products" p
            JOIN "Inventory" i
                ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
        ''')
        low_stock_count = cursor.fetchone()[0]

        # 30-day stock movement
        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
        ''')
        recent_stock_movement = cursor.fetchone()[0]

        # Recent stock transactions
        cursor.execute('''
            SELECT
                st.transaction_id,
                p.product_name,
                st.transaction_type,
                st.quantity,
                st.transaction_date
            FROM "StockTransactions" st
            JOIN "Products" p
                ON p.product_id = st.product_id
            ORDER BY st.transaction_date DESC
            LIMIT 5
        ''')
        transactions_rows = cursor.fetchall()
        recent_transactions = []
        for row in transactions_rows:
            recent_transactions.append({
                "transaction_id": row[0],
                "product_name": row[1],
                "transaction_type": row[2],
                "quantity": row[3],
                "transaction_date": row[4].isoformat() if row[4] else None
            })

        return {
            "active_pos": active_pos,
            "pending_po_value": pending_po_value,
            "low_stock_count": low_stock_count,
            "recent_stock_movement": recent_stock_movement,
            "recent_transactions": recent_transactions
        }

    finally:
        cursor.close()
        conn.close()


def get_owner_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Total users
        cursor.execute('SELECT COUNT(*) FROM "Users"')
        total_users = cursor.fetchone()[0]

        # Total registered suppliers
        cursor.execute('SELECT COUNT(*) FROM "Suppliers"')
        total_suppliers = cursor.fetchone()[0]

        # Total products in catalog
        cursor.execute('SELECT COUNT(*) FROM "Products"')
        total_products = cursor.fetchone()[0]

        # Total inventory value: SUM(selling_price * quantity_available)
        cursor.execute('''
            SELECT COALESCE(SUM(p.selling_price * i.quantity_available), 0)
            FROM "Products" p
            JOIN "Inventory" i
                ON p.product_id = i.product_id
        ''')
        total_inventory_value = float(cursor.fetchone()[0])

        # Recent system audit logs (last 5)
        cursor.execute('''
            SELECT
                al.log_id,
                al.action,
                COALESCE(u.username, 'System'),
                al.action_time,
                al.table_name,
                al.record_id,
                al.ip_address
            FROM "AuditLogs" al
            LEFT JOIN "Users" u
                ON al.user_id = u.user_id
            ORDER BY al.action_time DESC
            LIMIT 5
        ''')
        audit_rows = cursor.fetchall()
        recent_audits = []
        for row in audit_rows:
            action = row[1] or "Action"
            username = row[2]
            action_time = row[3]
            table_name = row[4] or "System"
            record_id = row[5]
            ip_address = row[6]

            readable_action = action.replace('_', ' ').title()
            if action.startswith('CREATE'):
                details = f"Added a new record in {table_name} (ID: {record_id})"
            elif action.startswith('UPDATE'):
                details = f"Updated a record in {table_name} (ID: {record_id})"
            elif action.startswith('DELETE'):
                details = f"Removed a record from {table_name} (ID: {record_id})"
            elif 'STATUS' in action:
                details = f"Changed status for {table_name} (ID: {record_id})"
            elif 'LOGIN' in action:
                details = f"User logged in from {ip_address or '127.0.0.1'}"
            elif 'STOCK' in action:
                details = f"Stock movement logged in {table_name} (ID: {record_id})"
            else:
                details = f"Modified {table_name} (Record ID: {record_id})"

            recent_audits.append({
                "log_id": row[0],
                "action": readable_action,
                "username": username,
                "timestamp": action_time.isoformat() if action_time else None,
                "details": details
            })

        return {
            "total_users": total_users,
            "total_suppliers": total_suppliers,
            "total_products": total_products,
            "total_inventory_value": total_inventory_value,
            "recent_audits": recent_audits
        }

    finally:
        cursor.close()
        conn.close()