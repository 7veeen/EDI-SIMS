from app.extensions import get_db_connection


def get_employee_dashboard(user_id=None):
    """
    Get live database-driven dashboard metrics for the authenticated Employee.
    Strictly isolated: queries assigned shipments, awaiting Stock-In tasks,
    employee-specific stock transactions, and relevant notifications.
    Preserves backward-compatible keys: total_products, total_stock, stock_in,
    stock_out, low_stock_products, tasks.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Total number of products (System-wide)
        cursor.execute('SELECT COUNT(*) FROM "Products"')
        total_products = int(cursor.fetchone()[0] or 0)

        # Total available stock (System-wide)
        cursor.execute('SELECT COALESCE(SUM(quantity_available), 0) FROM "Inventory"')
        total_stock = int(cursor.fetchone()[0] or 0)

        # Enterprise-wide stock in & out (preserved for backward compatibility with existing tests)
        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_type = 'STOCK_IN'
        ''')
        stock_in = int(cursor.fetchone()[0] or 0)

        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_type = 'STOCK_OUT'
        ''')
        stock_out = int(cursor.fetchone()[0] or 0)

        # Low-stock products using dynamic reorder level with enriched catalog fields
        cursor.execute('''
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                COALESCE(c.category_name, 'General') AS category_name,
                i.quantity_available,
                COALESCE(p.reorder_level, 10) AS reorder_level
            FROM "Products" p
            JOIN "Inventory" i
                ON p.product_id = i.product_id
            LEFT JOIN "Categories" c
                ON p.category_id = c.category_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
            ORDER BY i.quantity_available ASC
        ''')
        low_stock_rows = cursor.fetchall()
        low_stock_products = []
        for row in low_stock_rows:
            qty = int(row[4] or 0)
            reorder = int(row[5] or 10)
            stock_status = "Out of Stock" if qty <= 0 else "Low Stock"
            low_stock_products.append({
                "product_id": row[0],
                "product_name": row[1],
                "sku": row[2] or "",
                "category_name": row[3],
                "quantity_available": qty,
                "reorder_level": reorder,
                "stock_status": stock_status
            })

        # Employee Identity & Isolation
        employee_name = "Employee"
        tasks = []
        assigned_shipments = []
        attention_items = []
        recent_transactions = []
        assigned_shipments_count = 0
        awaiting_stock_in_count = 0
        in_transit_shipments_count = 0
        ready_shipments_count = 0
        fully_received_shipments_count = 0
        completed_stock_ins_count = 0
        completed_stock_ins_qty = 0
        completed_stock_outs_count = 0
        completed_stock_outs_qty = 0

        uid = None
        if user_id:
            try:
                uid = int(user_id)
            except (ValueError, TypeError):
                uid = None

        if uid:
            # 1. Resolve employee username
            cursor.execute('SELECT username FROM "Users" WHERE user_id = %s', (uid,))
            u_row = cursor.fetchone()
            if u_row:
                employee_name = u_row[0]

            # 2. Unread notifications for this employee
            cursor.execute('''
                SELECT notification_id, title, message, created_at, is_read
                FROM "Notifications"
                WHERE user_id = %s AND is_read = false
                ORDER BY created_at DESC
                LIMIT 10
            ''', (uid,))
            notif_rows = cursor.fetchall()
            for row in notif_rows:
                tasks.append({
                    "notification_id": row[0],
                    "title": row[1],
                    "message": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "is_read": row[4]
                })

            # 3. Shipments assigned to this authenticated employee
            cursor.execute('''
                SELECT 
                    shp.shipment_id,
                    shp.shipment_number,
                    shp.purchase_order_id,
                    shp.supplier_id,
                    s.supplier_name,
                    shp.carrier,
                    shp.tracking_number,
                    shp.status,
                    COALESCE(shp.receiving_status, 'Pending Receipt') AS receiving_status,
                    shp.expected_delivery,
                    shp.created_at,
                    COALESCE(poi_exp.total_expected, 0) AS total_expected,
                    COALESCE(st_rec.total_received, 0) AS total_received
                FROM "Shipments" shp
                JOIN "Suppliers" s ON shp.supplier_id = s.supplier_id
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
                WHERE shp.assigned_employee_id = %s
                ORDER BY shp.shipment_id DESC
            ''', (uid,))
            shp_rows = cursor.fetchall()

            assigned_shipments_count = len(shp_rows)
            for r in shp_rows:
                s_id = r[0]
                s_num = r[1]
                po_id = r[2]
                s_status = r[7] or "Ready for Shipment"
                rec_status = r[8] or "Pending Receipt"
                exp_qty = int(r[11] or 0)
                rec_qty = int(r[12] or 0)
                rem_qty = max(0, exp_qty - rec_qty)
                is_delivered = (s_status.lower() == 'delivered')
                can_stock_in = is_delivered and rem_qty > 0

                s_dict = {
                    "shipment_id": s_id,
                    "shipment_number": s_num,
                    "purchase_order_id": po_id,
                    "supplier_id": r[3],
                    "supplier_name": r[4],
                    "carrier": r[5] or "Standard Courier",
                    "tracking_number": r[6] or "",
                    "status": s_status,
                    "receiving_status": rec_status,
                    "expected_delivery": str(r[9]) if r[9] else None,
                    "created_at": r[10].isoformat() if r[10] else None,
                    "total_expected_quantity": exp_qty,
                    "total_received_quantity": rec_qty,
                    "total_remaining_quantity": rem_qty,
                    "can_stock_in": can_stock_in
                }
                assigned_shipments.append(s_dict)

                if s_status.lower() in ('dispatched', 'in transit'):
                    in_transit_shipments_count += 1
                elif s_status.lower() == 'ready for shipment':
                    ready_shipments_count += 1

                if rec_status == 'Fully Received' or (exp_qty > 0 and rec_qty >= exp_qty):
                    fully_received_shipments_count += 1
                elif is_delivered:
                    awaiting_stock_in_count += 1
                    attention_items.append({
                        "type": "shipment_receiving",
                        "shipment_id": s_id,
                        "shipment_number": s_num,
                        "purchase_order_id": po_id,
                        "supplier_name": r[4],
                        "status": s_status,
                        "receiving_status": rec_status,
                        "total_expected": exp_qty,
                        "total_received": rec_qty,
                        "total_remaining": rem_qty,
                        "title": f"Shipment {s_num} Ready for Stock-In",
                        "description": f"Delivered by {r[4]} (PO #{po_id}). {rem_qty} of {exp_qty} units awaiting goods receipt.",
                        "priority": "Urgent" if rem_qty >= 20 else "Action Required",
                        "action_label": "Receive Stock →",
                        "target_page": "shipments"
                    })

            # 4. Completed stock-in metrics performed by this employee
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(quantity), 0)
                FROM "StockTransactions"
                WHERE user_id = %s AND transaction_type = 'STOCK_IN'
            ''', (uid,))
            si_row = cursor.fetchone()
            completed_stock_ins_count = int(si_row[0] or 0)
            completed_stock_ins_qty = int(si_row[1] or 0)

            # 5. Completed stock-out metrics performed by this employee
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(quantity), 0)
                FROM "StockTransactions"
                WHERE user_id = %s AND transaction_type = 'STOCK_OUT'
            ''', (uid,))
            so_row = cursor.fetchone()
            completed_stock_outs_count = int(so_row[0] or 0)
            completed_stock_outs_qty = int(so_row[1] or 0)

            # 6. Latest 5 StockTransactions performed by this employee
            cursor.execute('''
                SELECT 
                    st.transaction_id,
                    st.product_id,
                    p.product_name,
                    p.sku,
                    st.transaction_type,
                    st.quantity,
                    st.transaction_date,
                    st.shipment_id,
                    shp.shipment_number,
                    st.notes
                FROM "StockTransactions" st
                JOIN "Products" p ON st.product_id = p.product_id
                LEFT JOIN "Shipments" shp ON st.shipment_id = shp.shipment_id
                WHERE st.user_id = %s
                ORDER BY st.transaction_date DESC, st.transaction_id DESC
                LIMIT 5
            ''', (uid,))
            tx_rows = cursor.fetchall()
            for t in tx_rows:
                recent_transactions.append({
                    "transaction_id": t[0],
                    "product_id": t[1],
                    "product_name": t[2],
                    "sku": t[3] or "",
                    "transaction_type": t[4],
                    "quantity": int(t[5] or 0),
                    "transaction_date": t[6].isoformat() if t[6] else None,
                    "shipment_id": t[7],
                    "shipment_number": t[8] or "",
                    "notes": t[9] or ""
                })

        return {
            # Backward-compatible existing keys
            "total_products": total_products,
            "total_stock": total_stock,
            "stock_in": stock_in,
            "stock_out": stock_out,
            "low_stock_products": low_stock_products,
            "tasks": tasks,
            # Enhanced Employee-specific metrics
            "employee_id": uid,
            "employee_name": employee_name,
            "assigned_shipments_count": assigned_shipments_count,
            "awaiting_stock_in": awaiting_stock_in_count,
            "in_transit_shipments": in_transit_shipments_count,
            "ready_shipments": ready_shipments_count,
            "fully_received_shipments": fully_received_shipments_count,
            "completed_stock_ins_count": completed_stock_ins_count,
            "completed_stock_ins_quantity": completed_stock_ins_qty,
            "completed_stock_outs_count": completed_stock_outs_count,
            "completed_stock_outs_quantity": completed_stock_outs_qty,
            "assigned_shipments": assigned_shipments,
            "attention_items": attention_items,
            "recent_transactions": recent_transactions,
            "low_stock_count": len(low_stock_products)
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
            "received_orders": total_purchase_orders,
            "completed_orders": raw_ship_counts.get("Delivered", 0),
            "total_order_value": total_order_value,
            "total_purchase_amount": total_order_value,
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
        # 1. Active purchase orders (orders that are not Completed, Rejected, or Cancelled)
        cursor.execute('''
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE status NOT IN ('Completed', 'Rejected', 'Cancelled')
        ''')
        active_pos = cursor.fetchone()[0]

        # 2. Pending purchase order value (value of purchase orders awaiting fulfillment)
        cursor.execute('''
            SELECT COALESCE(SUM(total_amount), 0)
            FROM "PurchaseOrders"
            WHERE status NOT IN ('Completed', 'Rejected', 'Cancelled')
        ''')
        pending_po_value = float(cursor.fetchone()[0])

        # 3. Low-stock count using dynamic reorder level from Products
        cursor.execute('''
            SELECT COUNT(*)
            FROM "Products" p
            JOIN "Inventory" i
                ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
        ''')
        low_stock_count = cursor.fetchone()[0]

        # 4. Pending Quotations awaiting Manager review/approval
        cursor.execute('''
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE status IN ('Submitted', 'Pending', 'Under Review')
        ''')
        pending_quotations = cursor.fetchone()[0]

        # 5. Pending Deliveries (Delivered shipments awaiting receiving / Stock-In)
        cursor.execute('''
            SELECT COUNT(*)
            FROM "Shipments"
            WHERE status = 'Delivered' AND (receiving_status IS NULL OR receiving_status NOT IN ('Fully Received', 'Received'))
        ''')
        pending_deliveries = cursor.fetchone()[0]

        # 6. Detailed Shipment Status counts
        cursor.execute('''
            SELECT status, COUNT(*)
            FROM "Shipments"
            GROUP BY status
        ''')
        raw_ship_counts = dict(cursor.fetchall())

        cursor.execute('''
            SELECT COUNT(*)
            FROM "Shipments"
            WHERE status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE
        ''')
        delayed_shipments = cursor.fetchone()[0]

        shipment_stats = {
            "ready_for_shipment": raw_ship_counts.get("Ready for Shipment", 0),
            "dispatched": raw_ship_counts.get("Dispatched", 0),
            "in_transit": raw_ship_counts.get("In Transit", 0),
            "delayed": delayed_shipments,
            "delivered": raw_ship_counts.get("Delivered", 0),
            "total": sum(raw_ship_counts.values())
        }

        # 7. Actionable Items for "Needs Your Attention"
        attention_items = []

        # (a) Quotations awaiting Manager approval
        cursor.execute('''
            SELECT q.quotation_id, q.quotation_number, sup.supplier_name, q.total_amount, q.status, q.quotation_date
            FROM "SupplierQuotations" q
            LEFT JOIN "Suppliers" sup ON q.supplier_id = sup.supplier_id
            WHERE q.status IN ('Submitted', 'Pending', 'Under Review')
            ORDER BY q.quotation_date DESC NULLS LAST
            LIMIT 4
        ''')
        for q in cursor.fetchall():
            q_num = q[1] or f"QT-{q[0]}"
            sup_name = q[2] or "Registered Supplier"
            amt = float(q[3]) if q[3] is not None else 0.0
            attention_items.append({
                "type": "quotation",
                "id": q[0],
                "reference": q_num,
                "title": f"Quotation {q_num} awaits approval",
                "description": f"Supplier: {sup_name} • Value: ₹{amt:,.2f}",
                "date": q[5].isoformat() if q[5] else None,
                "status": q[4],
                "priority": "High",
                "target_page": "quotations",
                "action_label": "Review"
            })

        # (b) Low-Stock critical products requiring replenishment
        cursor.execute('''
            SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
            ORDER BY (i.quantity_available - COALESCE(p.reorder_level, 10)) ASC
            LIMIT 4
        ''')
        for p in cursor.fetchall():
            avail = p[3]
            reorder = p[4] or 10
            attention_items.append({
                "type": "low_stock",
                "id": p[0],
                "reference": p[2] or f"PROD-{p[0]}",
                "title": f"Low Stock: {p[1]}",
                "description": f"SKU: {p[2]} • Available: {avail} (Reorder level: {reorder})",
                "date": None,
                "status": "Low Stock",
                "priority": "Urgent" if avail == 0 else "High",
                "target_page": "stock-requests",
                "action_label": "Restock"
            })

        # (c) Delivered shipments awaiting receiving / Stock-In
        cursor.execute('''
            SELECT s.shipment_id, s.shipment_number, s.purchase_order_id, sup.supplier_name, s.status, s.receiving_status, s.delivered_at
            FROM "Shipments" s
            LEFT JOIN "Suppliers" sup ON s.supplier_id = sup.supplier_id
            WHERE s.status = 'Delivered' AND (s.receiving_status IS NULL OR s.receiving_status NOT IN ('Fully Received', 'Received'))
            ORDER BY s.delivered_at DESC NULLS LAST
            LIMIT 4
        ''')
        for sh in cursor.fetchall():
            sh_num = sh[1] or f"SHP-{sh[0]}"
            sup_name = sh[3] or "Supplier"
            po_ref = f"PO #{sh[2]}" if sh[2] else "N/A"
            attention_items.append({
                "type": "delivery",
                "id": sh[0],
                "reference": sh_num,
                "title": f"Shipment {sh_num} delivered, pending Stock-In",
                "description": f"{sup_name} • Order: {po_ref}",
                "date": sh[6].strftime("%Y-%m-%d") if sh[6] else None,
                "status": "Pending Stock-In",
                "priority": "High",
                "target_page": "shipments",
                "action_label": "Receive"
            })

        # 8. Recent Purchase Orders for Manager table
        cursor.execute('''
            SELECT po.purchase_order_id, po.order_date, po.expected_delivery, po.total_amount, po.status, sup.supplier_name
            FROM "PurchaseOrders" po
            LEFT JOIN "Suppliers" sup ON po.supplier_id = sup.supplier_id
            ORDER BY po.order_date DESC NULLS LAST
            LIMIT 5
        ''')
        recent_orders = []
        for rpo in cursor.fetchall():
            recent_orders.append({
                "purchase_order_id": rpo[0],
                "order_date": rpo[1].isoformat() if rpo[1] else None,
                "expected_delivery": rpo[2].isoformat() if rpo[2] else None,
                "total_amount": float(rpo[3]) if rpo[3] is not None else 0.0,
                "status": rpo[4],
                "supplier_name": rpo[5] or "Unassigned"
            })

        # 9. Critical Low Stock items table
        cursor.execute('''
            SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
            ORDER BY (i.quantity_available - COALESCE(p.reorder_level, 10)) ASC
            LIMIT 5
        ''')
        critical_low_stock = []
        for cls_row in cursor.fetchall():
            critical_low_stock.append({
                "product_id": cls_row[0],
                "product_name": cls_row[1],
                "sku": cls_row[2] or f"PROD-{cls_row[0]}",
                "quantity_available": cls_row[3],
                "reorder_level": cls_row[4] or 10,
                "status": "Out of Stock" if cls_row[3] == 0 else "Low Stock"
            })

        # 10. Stock Requests Overview & Recent Requests
        cursor.execute('''
            SELECT status, COUNT(*)
            FROM "StockRequests"
            GROUP BY status
        ''')
        sr_counts = dict(cursor.fetchall())
        stock_requests_overview = {
            "pending": sr_counts.get("Pending", 0) + sr_counts.get("Open", 0),
            "quoted": sr_counts.get("Quoted", 0),
            "rejected": sr_counts.get("Rejected", 0),
            "total": sum(sr_counts.values())
        }

        cursor.execute('''
            SELECT sr.stock_request_id, sr.request_number, sr.priority, sr.status, sr.required_date, sr.created_at,
                   (SELECT p.product_name FROM "StockRequestItems" sri JOIN "Products" p ON sri.product_id = p.product_id WHERE sri.stock_request_id = sr.stock_request_id LIMIT 1) AS primary_product,
                   (SELECT COALESCE(SUM(sri.requested_quantity), 0) FROM "StockRequestItems" sri WHERE sri.stock_request_id = sr.stock_request_id) AS total_qty,
                   sup.supplier_name
            FROM "StockRequests" sr
            LEFT JOIN "Suppliers" sup ON sr.supplier_id = sup.supplier_id
            ORDER BY sr.created_at DESC
            LIMIT 5
        ''')
        recent_stock_requests = []
        for srr in cursor.fetchall():
            recent_stock_requests.append({
                "stock_request_id": srr[0],
                "request_number": srr[1],
                "priority": srr[2] or "Medium",
                "status": srr[3],
                "required_date": srr[4].isoformat() if srr[4] else None,
                "created_at": srr[5].isoformat() if srr[5] else None,
                "primary_product": srr[6] or "Catalog Restock",
                "total_quantity": int(srr[7]),
                "supplier_name": srr[8] or "Open Market"
            })

        # 11. 30-day stock movement
        cursor.execute('''
            SELECT COALESCE(SUM(quantity), 0)
            FROM "StockTransactions"
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
        ''')
        recent_stock_movement = cursor.fetchone()[0]

        # 12. Recent stock transactions
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

        # 13. Recent Operational Activity from OrderStatusHistory
        cursor.execute('''
            SELECT history_id, purchase_order_id, shipment_id, status, action, notes, changed_by, created_at
            FROM "OrderStatusHistory"
            ORDER BY created_at DESC
            LIMIT 6
        ''')
        recent_activity = []
        for act in cursor.fetchall():
            recent_activity.append({
                "history_id": act[0],
                "purchase_order_id": act[1],
                "shipment_id": act[2],
                "status": act[3],
                "action": act[4] or "STATUS_CHANGE",
                "notes": act[5] or "",
                "changed_by": act[6] or "System",
                "created_at": act[7].isoformat() if act[7] else None
            })

        return {
            "active_pos": active_pos,
            "pending_po_value": pending_po_value,
            "low_stock_count": low_stock_count,
            "pending_quotations": pending_quotations,
            "pending_deliveries": pending_deliveries,
            "shipment_stats": shipment_stats,
            "attention_items": attention_items,
            "recent_orders": recent_orders,
            "critical_low_stock": critical_low_stock,
            "stock_requests_overview": stock_requests_overview,
            "recent_stock_requests": recent_stock_requests,
            "recent_stock_movement": recent_stock_movement,
            "recent_transactions": recent_transactions,
            "recent_activity": recent_activity
        }

    finally:
        cursor.close()
        conn.close()


def get_owner_dashboard():
    """
    Get comprehensive executive-level dashboard metrics for the Owner role.
    Organization-wide visibility across all workflows: Inventory, Procurement,
    Quotations, Shipments, Users/Roles, System Health, and Audit activity.
    Preserves all existing response keys: total_users, total_suppliers,
    total_products, total_inventory_value, recent_audits.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Users Breakdown (Total, Active, Inactive, and Grouped by Role)
        cursor.execute('''
            SELECT r.role_name, u.status, COUNT(*)
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            GROUP BY r.role_name, u.status
        ''')
        user_rows = cursor.fetchall()
        total_users = 0
        active_users_count = 0
        inactive_users_count = 0
        users_by_role = {}
        for role_name, status, count in user_rows:
            total_users += count
            if status == "Active":
                active_users_count += count
            else:
                inactive_users_count += count
            if role_name not in users_by_role:
                users_by_role[role_name] = {"total": 0, "active": 0, "inactive": 0}
            users_by_role[role_name]["total"] += count
            if status == "Active":
                users_by_role[role_name]["active"] += count
            else:
                users_by_role[role_name]["inactive"] += count

        # 2. Total registered suppliers
        cursor.execute('SELECT COUNT(*) FROM "Suppliers"')
        total_suppliers = cursor.fetchone()[0] or 0

        # 3. Product Catalog & Inventory Health
        cursor.execute('''
            SELECT 
                COUNT(p.product_id) as total_products,
                COALESCE(SUM(i.quantity_available), 0) as total_units,
                COALESCE(SUM(p.selling_price * i.quantity_available), 0) as total_inventory_value,
                COUNT(CASE WHEN i.quantity_available <= p.reorder_level THEN 1 END) as low_stock_count,
                COUNT(CASE WHEN i.quantity_available = 0 THEN 1 END) as out_of_stock_count
            FROM "Products" p
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
        ''')
        inv_row = cursor.fetchone()
        total_products = int(inv_row[0] or 0)
        total_units = int(inv_row[1] or 0)
        total_inventory_value = float(inv_row[2] or 0.0)
        low_stock_count = int(inv_row[3] or 0)
        out_of_stock_count = int(inv_row[4] or 0)

        # 4. Stock Movement Throughput (Received vs Issued Volume)
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'STOCK_IN' THEN quantity ELSE 0 END), 0) as received_units,
                COALESCE(SUM(CASE WHEN transaction_type = 'STOCK_OUT' THEN quantity ELSE 0 END), 0) as issued_units,
                COUNT(*) as total_transactions
            FROM "StockTransactions"
        ''')
        tx_row = cursor.fetchone()
        received_units = int(tx_row[0] or 0)
        issued_units = int(tx_row[1] or 0)
        total_transactions = int(tx_row[2] or 0)

        # 5. Purchase Orders & Financial Spend Overview
        cursor.execute('''
            SELECT status, COUNT(*), COALESCE(SUM(total_amount), 0)
            FROM "PurchaseOrders"
            GROUP BY status
        ''')
        po_rows = cursor.fetchall()
        active_pos_count = 0
        active_pos_value = 0.0
        po_status_breakdown = {}
        total_pos_count = 0
        for status_val, count, val in po_rows:
            total_pos_count += count
            po_status_breakdown[status_val] = {
                "count": count,
                "value": float(val or 0.0)
            }
            if status_val in ('Pending', 'Accepted'):
                active_pos_count += count
                active_pos_value += float(val or 0.0)

        # 6. Pending Quotations Overview
        cursor.execute('''
            SELECT COUNT(*) 
            FROM "SupplierQuotations" 
            WHERE status IN ('Submitted', 'Pending', 'Under Review')
        ''')
        pending_quotations_count = int(cursor.fetchone()[0] or 0)

        # 7. Recent Purchase Orders (Latest 5)
        cursor.execute('''
            SELECT 
                po.purchase_order_id, 
                s.supplier_name, 
                po.order_date, 
                po.expected_delivery, 
                po.total_amount, 
                po.status 
            FROM "PurchaseOrders" po 
            LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id 
            ORDER BY po.order_date DESC, po.purchase_order_id DESC 
            LIMIT 5
        ''')
        recent_orders_rows = cursor.fetchall()
        recent_orders = []
        for r in recent_orders_rows:
            recent_orders.append({
                "purchase_order_id": r[0],
                "supplier_name": r[1] or "Unknown Supplier",
                "order_date": r[2].isoformat() if r[2] else None,
                "expected_delivery": r[3].isoformat() if r[3] else None,
                "total_amount": float(r[4] or 0.0),
                "status": r[5]
            })

        # 8. Shipment & Logistics Statistics
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN status = 'Ready for Shipment' THEN 1 END) as ready,
                COUNT(CASE WHEN status IN ('Dispatched', 'In Transit') THEN 1 END) as in_transit,
                COUNT(CASE WHEN status = 'Delivered' THEN 1 END) as delivered,
                COUNT(*) as total
            FROM "Shipments"
        ''')
        ship_row = cursor.fetchone()
        shipment_stats = {
            "ready_for_shipment": int(ship_row[0] or 0),
            "in_transit": int(ship_row[1] or 0),
            "delivered": int(ship_row[2] or 0),
            "total_shipments": int(ship_row[3] or 0)
        }

        # 9. Latest Database Backup
        cursor.execute('''
            SELECT backup_id, backup_name, backup_type, backup_date, backup_size, status
            FROM "BackupHistory"
            ORDER BY backup_id DESC LIMIT 1
        ''')
        bk_row = cursor.fetchone()
        latest_backup = None
        if bk_row:
            latest_backup = {
                "backup_id": bk_row[0],
                "backup_name": bk_row[1],
                "backup_type": bk_row[2],
                "backup_date": bk_row[3].isoformat() if bk_row[3] else None,
                "backup_size": bk_row[4],
                "status": bk_row[5]
            }

        # 10. System Health Summary
        cursor.execute('''
            SELECT status_id, module_name, status, progress, message, updated_at
            FROM "SystemStatus"
            ORDER BY status_id ASC LIMIT 1
        ''')
        sys_row = cursor.fetchone()
        system_status = None
        if sys_row:
            system_status = {
                "module_name": sys_row[1],
                "status": sys_row[2],
                "progress": sys_row[3],
                "message": sys_row[4],
                "updated_at": sys_row[5].isoformat() if sys_row[5] else None
            }

        # 11. Needs Your Attention Items (Real live pending decisions)
        attention_items = []

        # A. Pending Quotations Awaiting Approval
        cursor.execute('''
            SELECT 
                sq.quotation_id, 
                sq.quotation_number, 
                s.supplier_name, 
                p.product_name, 
                sq.total_amount, 
                sq.status, 
                sq.quotation_date
            FROM "SupplierQuotations" sq
            LEFT JOIN "Suppliers" s ON sq.supplier_id = s.supplier_id
            LEFT JOIN "Products" p ON sq.product_id = p.product_id
            WHERE sq.status IN ('Submitted', 'Pending', 'Under Review')
            ORDER BY sq.quotation_date DESC, sq.quotation_id DESC
            LIMIT 4
        ''')
        for q_row in cursor.fetchall():
            q_id = q_row[0]
            q_num = q_row[1] or f"QTN-{q_id:04d}"
            s_name = q_row[2] or "Supplier"
            p_name = q_row[3] or "Product"
            amt = float(q_row[4] or 0.0)
            attention_items.append({
                "type": "quotation",
                "id": q_id,
                "title": f"Quotation {q_num} ({s_name})",
                "subtitle": f"{p_name} — Total: ₹{amt:,.2f}",
                "status": q_row[5],
                "badge": "Awaiting Approval",
                "badge_color": "warning",
                "action_label": "Review →",
                "action_route": "quotations"
            })

        # B. Critical Low Stock Products
        cursor.execute('''
            SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = p.product_id
            WHERE i.quantity_available <= p.reorder_level
            ORDER BY i.quantity_available ASC
            LIMIT 3
        ''')
        for p_row in cursor.fetchall():
            prod_id = p_row[0]
            prod_name = p_row[1]
            sku = p_row[2]
            qty = p_row[3]
            reorder = p_row[4]
            attention_items.append({
                "type": "low_stock",
                "id": prod_id,
                "title": f"Low Stock: {prod_name}",
                "subtitle": f"Available: {qty} units (Reorder point: {reorder}) • SKU: {sku}",
                "status": "Low Stock",
                "badge": "Action Required",
                "badge_color": "danger",
                "action_label": "Restock →",
                "action_route": "inventory"
            })

        # C. Pending Purchase Orders Awaiting Response
        cursor.execute('''
            SELECT po.purchase_order_id, s.supplier_name, po.total_amount, po.status, po.order_date
            FROM "PurchaseOrders" po
            LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
            WHERE po.status = 'Pending'
            ORDER BY po.order_date DESC, po.purchase_order_id DESC
            LIMIT 3
        ''')
        for po_item in cursor.fetchall():
            po_id = po_item[0]
            s_name = po_item[1] or "Supplier"
            po_amt = float(po_item[2] or 0.0)
            attention_items.append({
                "type": "purchase_order",
                "id": po_id,
                "title": f"Purchase Order #{po_id:04d} ({s_name})",
                "subtitle": f"Value: ₹{po_amt:,.2f} — Waiting for supplier response",
                "status": po_item[3],
                "badge": "Pending Response",
                "badge_color": "info",
                "action_label": "View →",
                "action_route": "purchase-orders"
            })

        # 12. Recent System Audit Logs (last 5, preserved)
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
            # Backward-compatible keys
            "total_users": total_users,
            "total_suppliers": total_suppliers,
            "total_products": total_products,
            "total_inventory_value": total_inventory_value,
            "recent_audits": recent_audits,

            # Extended executive metrics
            "active_pos_count": active_pos_count,
            "active_pos_value": active_pos_value,
            "total_pos_count": total_pos_count,
            "pending_quotations_count": pending_quotations_count,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "active_users_count": active_users_count,
            "inactive_users_count": inactive_users_count,
            "users_by_role": users_by_role,
            "po_status_breakdown": po_status_breakdown,
            "recent_orders": recent_orders,
            "shipment_stats": shipment_stats,
            "inventory_health": {
                "total_products": total_products,
                "total_units": total_units,
                "total_inventory_value": total_inventory_value,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "received_units": received_units,
                "issued_units": issued_units,
                "total_transactions": total_transactions
            },
            "attention_items": attention_items,
            "latest_backup": latest_backup,
            "system_status": system_status
        }

    finally:
        cursor.close()
        conn.close()