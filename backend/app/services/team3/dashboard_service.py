from app.extensions import get_db_connection


def get_employee_dashboard(user_id=None):
    """
    Get live database-driven dashboard metrics for the authenticated Employee.
    Strictly isolated: queries assigned shipments, awaiting Stock-In tasks,
    employee-specific stock transactions, and relevant notifications.
    Consolidated into two optimized round-trips:
      1. System-wide catalog and inventory aggregates
      2. Authenticated employee scoped tasks, shipments, and transaction metrics
    Preserves backward-compatible keys: total_products, total_stock, stock_in,
    stock_out, low_stock_products, tasks.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query 1: System-wide metrics & catalog low-stock items
        q_system = '''
        SELECT
          (SELECT COUNT(*) FROM "Products") AS total_products,
          (SELECT COALESCE(SUM(quantity_available), 0) FROM "Inventory") AS total_stock,
          (SELECT COALESCE(SUM(quantity), 0) FROM "StockTransactions" WHERE transaction_type = 'STOCK_IN') AS stock_in,
          (SELECT COALESCE(SUM(quantity), 0) FROM "StockTransactions" WHERE transaction_type = 'STOCK_OUT') AS stock_out,
          (SELECT json_agg(lsp_row) FROM (
             SELECT
               p.product_id,
               p.product_name,
               p.sku,
               COALESCE(c.category_name, 'General') AS category_name,
               i.quantity_available,
               COALESCE(p.reorder_level, 10) AS reorder_level
             FROM "Products" p
             JOIN "Inventory" i ON p.product_id = i.product_id
             LEFT JOIN "Categories" c ON p.category_id = c.category_id
             WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
             ORDER BY i.quantity_available ASC
           ) lsp_row) AS low_stock_products;
        '''

        cursor.execute(q_system)
        sys_row = cursor.fetchone()

        total_products = int(sys_row[0] or 0)
        total_stock = int(sys_row[1] or 0)
        stock_in = int(sys_row[2] or 0)
        stock_out = int(sys_row[3] or 0)

        low_stock_products = []
        for row in (sys_row[4] or []):
            qty = int(row['quantity_available'] or 0)
            reorder = int(row['reorder_level'] or 10)
            stock_status = "Out of Stock" if qty <= 0 else "Low Stock"
            low_stock_products.append({
                "product_id": row['product_id'],
                "product_name": row['product_name'],
                "sku": row['sku'] or "",
                "category_name": row['category_name'],
                "quantity_available": qty,
                "reorder_level": reorder,
                "stock_status": stock_status
            })

        # Employee Identity & Isolation defaults
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
            # Query 2: Consolidated employee tasks, shipments, stock actions, and transactions
            q_employee = '''
            WITH
              emp_user AS (
                SELECT username FROM "Users" WHERE user_id = %s
              ),
              emp_notifs AS (
                SELECT json_agg(n_row) AS data FROM (
                  SELECT notification_id, title, message, created_at, is_read
                  FROM "Notifications"
                  WHERE user_id = %s AND is_read = false
                  ORDER BY created_at DESC
                  LIMIT 10
                ) n_row
              ),
              emp_stock_in AS (
                SELECT COUNT(*) AS cnt, COALESCE(SUM(quantity), 0) AS qty
                FROM "StockTransactions"
                WHERE user_id = %s AND transaction_type = 'STOCK_IN'
              ),
              emp_stock_out AS (
                SELECT COUNT(*) AS cnt, COALESCE(SUM(quantity), 0) AS qty
                FROM "StockTransactions"
                WHERE user_id = %s AND transaction_type = 'STOCK_OUT'
              ),
              emp_shipments AS (
                SELECT json_agg(shp_row) AS data FROM (
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
                ) shp_row
              ),
              emp_recent_tx AS (
                SELECT json_agg(tx_row) AS data FROM (
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
                ) tx_row
              )
            SELECT
              (SELECT username FROM emp_user) AS employee_name,
              (SELECT data FROM emp_notifs) AS notifications,
              (SELECT row_to_json(emp_stock_in.*) FROM emp_stock_in) AS stock_in_stats,
              (SELECT row_to_json(emp_stock_out.*) FROM emp_stock_out) AS stock_out_stats,
              (SELECT data FROM emp_shipments) AS shipments,
              (SELECT data FROM emp_recent_tx) AS recent_transactions;
            '''

            cursor.execute(q_employee, (uid, uid, uid, uid, uid, uid))
            emp_res = cursor.fetchone()

            if emp_res[0]:
                employee_name = emp_res[0]

            for row in (emp_res[1] or []):
                tasks.append({
                    "notification_id": row['notification_id'],
                    "title": row['title'],
                    "message": row['message'],
                    "created_at": row['created_at'],
                    "is_read": row['is_read']
                })

            si_stats = emp_res[2] or {}
            completed_stock_ins_count = int(si_stats.get('cnt', 0))
            completed_stock_ins_qty = int(si_stats.get('qty', 0))

            so_stats = emp_res[3] or {}
            completed_stock_outs_count = int(so_stats.get('cnt', 0))
            completed_stock_outs_qty = int(so_stats.get('qty', 0))

            shp_rows = emp_res[4] or []
            assigned_shipments_count = len(shp_rows)
            for r in shp_rows:
                s_id = r['shipment_id']
                s_num = r['shipment_number']
                po_id = r['purchase_order_id']
                s_status = r['status'] or "Ready for Shipment"
                rec_status = r['receiving_status'] or "Pending Receipt"
                exp_qty = int(r['total_expected'] or 0)
                rec_qty = int(r['total_received'] or 0)
                rem_qty = max(0, exp_qty - rec_qty)
                is_delivered = (s_status.lower() == 'delivered')
                can_stock_in = is_delivered and rem_qty > 0

                s_dict = {
                    "shipment_id": s_id,
                    "shipment_number": s_num,
                    "purchase_order_id": po_id,
                    "supplier_id": r['supplier_id'],
                    "supplier_name": r['supplier_name'],
                    "carrier": r['carrier'] or "Standard Courier",
                    "tracking_number": r['tracking_number'] or "",
                    "status": s_status,
                    "receiving_status": rec_status,
                    "expected_delivery": str(r['expected_delivery']) if r['expected_delivery'] else None,
                    "created_at": r['created_at'],
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
                        "supplier_name": r['supplier_name'],
                        "status": s_status,
                        "receiving_status": rec_status,
                        "total_expected": exp_qty,
                        "total_received": rec_qty,
                        "total_remaining": rem_qty,
                        "title": f"Shipment {s_num} Ready for Stock-In",
                        "description": f"Delivered by {r['supplier_name']} (PO #{po_id}). {rem_qty} of {exp_qty} units awaiting goods receipt.",
                        "priority": "Urgent" if rem_qty >= 20 else "Action Required",
                        "action_label": "Receive Stock →",
                        "target_page": "shipments"
                    })

            for t in (emp_res[5] or []):
                recent_transactions.append({
                    "transaction_id": t['transaction_id'],
                    "product_id": t['product_id'],
                    "product_name": t['product_name'],
                    "sku": t['sku'] or "",
                    "transaction_type": t['transaction_type'],
                    "quantity": int(t['quantity'] or 0),
                    "transaction_date": t['transaction_date'],
                    "shipment_id": t['shipment_id'],
                    "shipment_number": t['shipment_number'] or "",
                    "notes": t['notes'] or ""
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
    Consolidated into two optimized round-trips:
      1. Supplier identity, profile fields, order/quotation/shipment aggregate counts and rates
      2. Attention items and recent orders/requests/audit history
    """
    if not user_id:
        return None, "Authenticated user identity required."

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        uid = int(user_id)

        # Query 1: Supplier profile and all scalar aggregates
        q_metrics = '''
        WITH
          sup_profile AS (
            SELECT supplier_id, supplier_name, contact_person, phone, email, status
            FROM "Suppliers"
            WHERE user_id = %(uid)s
          ),
          req_stats AS (
            SELECT 
              COUNT(CASE WHEN status IN ('Pending', 'Open') THEN 1 END) AS open_requests,
              COUNT(*) AS total_requests
            FROM "StockRequests"
            WHERE supplier_id = (SELECT supplier_id FROM sup_profile)
          ),
          quo_stats AS (
            SELECT
              COUNT(CASE WHEN status IN ('Pending', 'Submitted', 'Under Review') THEN 1 END) AS pending_quotations,
              COUNT(CASE WHEN status IN ('Approved', 'Accepted') THEN 1 END) AS approved_quotations,
              COUNT(CASE WHEN status IN ('Approved', 'Accepted', 'Rejected') THEN 1 END) AS resolved_quotations,
              COUNT(*) AS total_quotations
            FROM "SupplierQuotations"
            WHERE supplier_id = (SELECT supplier_id FROM sup_profile)
          ),
          po_stats AS (
            SELECT
              COUNT(CASE WHEN status NOT IN ('Completed', 'Rejected', 'Cancelled') THEN 1 END) AS active_pos,
              COUNT(*) AS total_purchase_orders,
              COALESCE(SUM(total_amount), 0) AS total_order_value,
              COUNT(CASE WHEN supplier_response = 'Accepted' THEN 1 END) AS po_accepted,
              COUNT(CASE WHEN supplier_response IN ('Accepted', 'Rejected') THEN 1 END) AS po_responded
            FROM "PurchaseOrders"
            WHERE supplier_id = (SELECT supplier_id FROM sup_profile)
          ),
          ship_counts AS (
            SELECT status, COUNT(*) AS cnt
            FROM "Shipments"
            WHERE supplier_id = (SELECT supplier_id FROM sup_profile)
            GROUP BY status
          ),
          ship_stats AS (
            SELECT
              COUNT(CASE WHEN status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE THEN 1 END) AS delayed,
              COUNT(CASE WHEN status NOT IN ('Delivered', 'Cancelled') THEN 1 END) AS pending_deliveries,
              COUNT(CASE WHEN status = 'Delivered' AND delivered_at IS NOT NULL AND (expected_delivery IS NULL OR delivered_at::date <= expected_delivery) THEN 1 END) AS on_time_deliveries,
              COUNT(CASE WHEN status = 'Delivered' AND delivered_at IS NOT NULL THEN 1 END) AS total_delivered_deliveries
            FROM "Shipments"
            WHERE supplier_id = (SELECT supplier_id FROM sup_profile)
          )
        SELECT
          (SELECT row_to_json(sup_profile.*) FROM sup_profile) AS profile,
          (SELECT row_to_json(req_stats.*) FROM req_stats) AS req_stats,
          (SELECT row_to_json(quo_stats.*) FROM quo_stats) AS quo_stats,
          (SELECT row_to_json(po_stats.*) FROM po_stats) AS po_stats,
          (SELECT json_object_agg(status, cnt) FROM ship_counts) AS raw_ship_counts,
          (SELECT row_to_json(ship_stats.*) FROM ship_stats) AS ship_stats;
        '''

        cursor.execute(q_metrics, {'uid': uid})
        m_row = cursor.fetchone()

        sup = m_row[0]
        if not sup:
            return None, "Supplier profile not found for authenticated user."

        supplier_id = sup['supplier_id']
        supplier_name = sup['supplier_name']
        contact_person = sup['contact_person'] or ""
        phone = sup['phone'] or ""
        email = sup['email'] or ""
        status = sup['status'] or "Active"

        req_stats = m_row[1] or {}
        open_requests = int(req_stats.get('open_requests', 0))
        total_requests = int(req_stats.get('total_requests', 0))

        quo_stats = m_row[2] or {}
        pending_quotations = int(quo_stats.get('pending_quotations', 0))
        approved_quotations = int(quo_stats.get('approved_quotations', 0))
        total_quotations = int(quo_stats.get('total_quotations', 0))
        quotation_approved = approved_quotations
        quotation_resolved = int(quo_stats.get('resolved_quotations', 0))
        quotation_acceptance_rate = round((quotation_approved / quotation_resolved) * 100, 1) if quotation_resolved > 0 else (
            100.0 if quotation_approved > 0 else None
        )

        po_stats = m_row[3] or {}
        active_pos = int(po_stats.get('active_pos', 0))
        total_purchase_orders = int(po_stats.get('total_purchase_orders', 0))
        total_order_value = float(po_stats.get('total_order_value', 0.0))
        po_accepted = int(po_stats.get('po_accepted', 0))
        po_responded = int(po_stats.get('po_responded', 0))
        order_acceptance_rate = round((po_accepted / po_responded) * 100, 1) if po_responded > 0 else (
            100.0 if po_accepted > 0 else None
        )

        raw_ship_counts = m_row[4] or {}
        ship_stats_raw = m_row[5] or {}
        pending_deliveries = int(ship_stats_raw.get('pending_deliveries', 0))
        delayed_deliveries = int(ship_stats_raw.get('delayed', 0))
        on_time_count = int(ship_stats_raw.get('on_time_deliveries', 0))
        total_deliveries = int(ship_stats_raw.get('total_delivered_deliveries', 0))
        on_time_delivery_rate = round((on_time_count / total_deliveries) * 100, 1) if total_deliveries > 0 else None

        shipment_stats = {
            "ready_for_shipment": int(raw_ship_counts.get("Ready for Shipment", 0)),
            "dispatched": int(raw_ship_counts.get("Dispatched", 0)),
            "in_transit": int(raw_ship_counts.get("In Transit", 0)),
            "delayed": delayed_deliveries,
            "delivered": int(raw_ship_counts.get("Delivered", 0)),
            "total": sum(int(v) for v in raw_ship_counts.values())
        }

        # Profile Completion Rate
        profile_fields = [supplier_name, contact_person, phone, email, status]
        filled_count = sum(1 for f in profile_fields if f and str(f).strip())
        profile_completion = int(round((filled_count / len(profile_fields)) * 100))

        # Payments placeholder
        pending_payments = None
        has_payment_module = False

        # Query 2: Lists & Attention items
        q_lists = '''
        SELECT
          -- recent_stock_requests (limit 5)
          (SELECT json_agg(sr_row) FROM (
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
             WHERE sr.supplier_id = %(sid)s AND sr.status IN ('Pending', 'Open')
             GROUP BY sr.stock_request_id
             ORDER BY sr.created_at DESC
             LIMIT 5
           ) sr_row) AS recent_stock_requests,

          -- recent_orders (limit 5)
          (SELECT json_agg(po_row) FROM (
             SELECT
                 purchase_order_id,
                 order_date,
                 expected_delivery,
                 total_amount,
                 status,
                 supplier_response
             FROM "PurchaseOrders"
             WHERE supplier_id = %(sid)s
             ORDER BY order_date DESC
             LIMIT 5
           ) po_row) AS recent_orders,

          -- attention_stock_requests (limit 5)
          (SELECT json_agg(asr_row) FROM (
             SELECT sr.stock_request_id, sr.request_number, sr.priority, sr.required_date, sr.created_at,
                    COALESCE((
                        SELECT p.product_name 
                        FROM "StockRequestItems" sri 
                        JOIN "Products" p ON sri.product_id = p.product_id 
                        WHERE sri.stock_request_id = sr.stock_request_id 
                        LIMIT 1
                    ), 'Restock Request') AS primary_product
             FROM "StockRequests" sr
             WHERE sr.supplier_id = %(sid)s AND sr.status IN ('Pending', 'Open')
             ORDER BY CASE WHEN sr.priority = 'Urgent' THEN 1 WHEN sr.priority = 'High' THEN 2 ELSE 3 END, sr.created_at DESC
             LIMIT 5
           ) asr_row) AS attention_stock_requests,

          -- attention_orders (limit 5)
          (SELECT json_agg(apo_row) FROM (
             SELECT po.purchase_order_id, po.order_date, po.total_amount, po.status, po.supplier_response
             FROM "PurchaseOrders" po
             WHERE po.supplier_id = %(sid)s AND (po.supplier_response = 'Pending' OR po.supplier_response IS NULL) AND po.status NOT IN ('Cancelled', 'Rejected', 'Delivered')
             ORDER BY po.order_date DESC
             LIMIT 5
           ) apo_row) AS attention_orders,

          -- attention_delayed_shipments (limit 5)
          (SELECT json_agg(ash_row) FROM (
             SELECT s.shipment_id, s.shipment_number, s.expected_delivery, s.status, s.purchase_order_id
             FROM "Shipments" s
             WHERE s.supplier_id = %(sid)s AND s.status NOT IN ('Delivered', 'Cancelled') AND s.expected_delivery < CURRENT_DATE
             ORDER BY s.expected_delivery ASC
             LIMIT 5
           ) ash_row) AS attention_delayed_shipments,

          -- recent_activity (limit 6)
          (SELECT json_agg(act_row) FROM (
             SELECT history_id, purchase_order_id, shipment_id, status, previous_status, action, notes, changed_by, created_at
             FROM "OrderStatusHistory"
             WHERE supplier_id = %(sid)s
             ORDER BY created_at DESC
             LIMIT 6
           ) act_row) AS recent_activity;
        '''

        cursor.execute(q_lists, {'sid': supplier_id})
        l_row = cursor.fetchone()

        recent_stock_requests = []
        for rr in (l_row[0] or []):
            recent_stock_requests.append({
                "stock_request_id": rr['stock_request_id'],
                "request_number": rr['request_number'],
                "priority": rr['priority'] or "Medium",
                "required_date": rr['required_date'],
                "created_at": rr['created_at'],
                "total_quantity": int(rr['total_qty']),
                "primary_product": rr['primary_product'] or "General Catalog"
            })

        recent_orders = []
        for rpo in (l_row[1] or []):
            recent_orders.append({
                "purchase_order_id": rpo['purchase_order_id'],
                "order_date": rpo['order_date'],
                "expected_delivery": rpo['expected_delivery'],
                "total_amount": float(rpo['total_amount']) if rpo['total_amount'] is not None else 0.0,
                "status": rpo['status'],
                "supplier_response": rpo['supplier_response'] or "Pending"
            })

        attention_items = []
        for sr in (l_row[2] or []):
            attention_items.append({
                "type": "stock_request",
                "id": sr['stock_request_id'],
                "reference": sr['request_number'],
                "title": f"Stock Request {sr['request_number']} needs response",
                "description": f"Priority: {sr['priority']} • Product: {sr['primary_product']}",
                "date": sr['required_date'],
                "status": "Pending",
                "priority": sr['priority'],
                "target_page": "stock-requests",
                "action_label": "Review"
            })

        for po in (l_row[3] or []):
            order_date_val = po['order_date']
            attention_items.append({
                "type": "purchase_order",
                "id": po['purchase_order_id'],
                "reference": f"PO #{po['purchase_order_id']}",
                "title": f"PO #{po['purchase_order_id']} is awaiting your acceptance",
                "description": f"Order value: ₹{float(po['total_amount']):,.2f} • Ordered: {order_date_val}",
                "date": order_date_val,
                "status": "Awaiting Acceptance",
                "priority": "High",
                "target_page": "purchase-orders",
                "action_label": "Review"
            })

        for sh in (l_row[4] or []):
            exp_date_val = sh['expected_delivery']
            attention_items.append({
                "type": "delayed_shipment",
                "id": sh['shipment_id'],
                "reference": sh['shipment_number'],
                "title": f"Shipment {sh['shipment_number']} is delayed",
                "description": f"Expected on {exp_date_val} for PO #{sh['purchase_order_id']}",
                "date": exp_date_val,
                "status": "Delayed",
                "priority": "Urgent",
                "target_page": "shipments",
                "action_label": "Track"
            })

        recent_activity = []
        for h in (l_row[5] or []):
            recent_activity.append({
                "history_id": h['history_id'],
                "purchase_order_id": h['purchase_order_id'],
                "shipment_id": h['shipment_id'],
                "status": h['status'],
                "previous_status": h['previous_status'],
                "action": h['action'] or "UPDATE",
                "notes": h['notes'] or "",
                "changed_by": h['changed_by'] or "System",
                "created_at": h['created_at']
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
            "completed_orders": int(raw_ship_counts.get("Delivered", 0)),
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
    """
    Get live database-driven dashboard metrics for the Manager role.
    Consolidated into two optimized round-trips:
      1. Scalar metrics: active POs, low stock count, pending quotations, pending deliveries,
         shipment status counts, stock requests overview, and 30-day stock movement
      2. Lists: attention quotations, attention low stock, attention deliveries,
         recent purchase orders, critical low stock, recent stock requests,
         recent stock transactions, and recent operational activity
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        q_metrics = '''
        WITH
          po_stats AS (
            SELECT 
                COUNT(*) AS active_pos, 
                COALESCE(SUM(total_amount), 0) AS pending_po_value
            FROM "PurchaseOrders"
            WHERE status NOT IN ('Completed', 'Rejected', 'Cancelled')
          ),
          ls_stats AS (
            SELECT COUNT(*) AS low_stock_count
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
          ),
          quo_stats AS (
            SELECT COUNT(*) AS pending_quotations
            FROM "SupplierQuotations"
            WHERE status IN ('Submitted', 'Pending', 'Under Review')
          ),
          deliv_stats AS (
            SELECT COUNT(*) AS pending_deliveries
            FROM "Shipments"
            WHERE status = 'Delivered' AND (receiving_status IS NULL OR receiving_status NOT IN ('Fully Received', 'Received'))
          ),
          ship_counts AS (
            SELECT status, COUNT(*) AS cnt
            FROM "Shipments"
            GROUP BY status
          ),
          ship_delayed AS (
            SELECT COUNT(*) AS delayed
            FROM "Shipments"
            WHERE status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE
          ),
          sr_counts AS (
            SELECT status, COUNT(*) AS cnt
            FROM "StockRequests"
            GROUP BY status
          ),
          movement_stats AS (
            SELECT COALESCE(SUM(quantity), 0) AS recent_stock_movement
            FROM "StockTransactions"
            WHERE transaction_date >= CURRENT_DATE - INTERVAL '30 days'
          )
        SELECT 
          (SELECT row_to_json(po_stats.*) FROM po_stats) AS po_stats,
          (SELECT low_stock_count FROM ls_stats) AS low_stock_count,
          (SELECT pending_quotations FROM quo_stats) AS pending_quotations,
          (SELECT pending_deliveries FROM deliv_stats) AS pending_deliveries,
          (SELECT json_object_agg(status, cnt) FROM ship_counts) AS ship_counts,
          (SELECT delayed FROM ship_delayed) AS delayed_shipments,
          (SELECT json_object_agg(status, cnt) FROM sr_counts) AS sr_counts,
          (SELECT recent_stock_movement FROM movement_stats) AS recent_stock_movement;
        '''

        q_lists = '''
        SELECT
          -- Quotations awaiting Manager approval (limit 4)
          (SELECT json_agg(q_row) FROM (
             SELECT q.quotation_id, q.quotation_number, sup.supplier_name, q.total_amount, q.status, q.quotation_date
             FROM "SupplierQuotations" q
             LEFT JOIN "Suppliers" sup ON q.supplier_id = sup.supplier_id
             WHERE q.status IN ('Submitted', 'Pending', 'Under Review')
             ORDER BY q.quotation_date DESC NULLS LAST
             LIMIT 4
           ) q_row) AS attention_quotations,

          -- Low-Stock critical products requiring replenishment (limit 4)
          (SELECT json_agg(als_row) FROM (
             SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
             FROM "Products" p
             JOIN "Inventory" i ON p.product_id = i.product_id
             WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
             ORDER BY (i.quantity_available - COALESCE(p.reorder_level, 10)) ASC
             LIMIT 4
           ) als_row) AS attention_low_stock,

          -- Delivered shipments awaiting receiving / Stock-In (limit 4)
          (SELECT json_agg(d_row) FROM (
             SELECT s.shipment_id, s.shipment_number, s.purchase_order_id, sup.supplier_name, s.status, s.receiving_status, s.delivered_at
             FROM "Shipments" s
             LEFT JOIN "Suppliers" sup ON s.supplier_id = sup.supplier_id
             WHERE s.status = 'Delivered' AND (s.receiving_status IS NULL OR s.receiving_status NOT IN ('Fully Received', 'Received'))
             ORDER BY s.delivered_at DESC NULLS LAST
             LIMIT 4
           ) d_row) AS attention_deliveries,

          -- Recent Purchase Orders (limit 5)
          (SELECT json_agg(po_row) FROM (
             SELECT po.purchase_order_id, po.order_date, po.expected_delivery, po.total_amount, po.status, sup.supplier_name
             FROM "PurchaseOrders" po
             LEFT JOIN "Suppliers" sup ON po.supplier_id = sup.supplier_id
             ORDER BY po.order_date DESC NULLS LAST
             LIMIT 5
           ) po_row) AS recent_orders,

          -- Critical Low Stock items table (limit 5)
          (SELECT json_agg(cls_row) FROM (
             SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
             FROM "Products" p
             JOIN "Inventory" i ON p.product_id = i.product_id
             WHERE i.quantity_available <= COALESCE(p.reorder_level, 10)
             ORDER BY (i.quantity_available - COALESCE(p.reorder_level, 10)) ASC
             LIMIT 5
           ) cls_row) AS critical_low_stock,

          -- Recent stock requests (limit 5)
          (SELECT json_agg(sr_row) FROM (
             SELECT sr.stock_request_id, sr.request_number, sr.priority, sr.status, sr.required_date, sr.created_at,
                    (SELECT p.product_name FROM "StockRequestItems" sri JOIN "Products" p ON sri.product_id = p.product_id WHERE sri.stock_request_id = sr.stock_request_id LIMIT 1) AS primary_product,
                    (SELECT COALESCE(SUM(sri.requested_quantity), 0) FROM "StockRequestItems" sri WHERE sri.stock_request_id = sr.stock_request_id) AS total_qty,
                    sup.supplier_name
             FROM "StockRequests" sr
             LEFT JOIN "Suppliers" sup ON sr.supplier_id = sup.supplier_id
             ORDER BY sr.created_at DESC
             LIMIT 5
           ) sr_row) AS recent_stock_requests,

          -- Recent transactions (limit 5)
          (SELECT json_agg(st_row) FROM (
             SELECT st.transaction_id, p.product_name, st.transaction_type, st.quantity, st.transaction_date
             FROM "StockTransactions" st
             JOIN "Products" p ON p.product_id = st.product_id
             ORDER BY st.transaction_date DESC
             LIMIT 5
           ) st_row) AS recent_transactions,

          -- Recent Operational Activity from OrderStatusHistory (limit 6)
          (SELECT json_agg(act_row) FROM (
             SELECT history_id, purchase_order_id, shipment_id, status, action, notes, changed_by, created_at
             FROM "OrderStatusHistory"
             ORDER BY created_at DESC
             LIMIT 6
           ) act_row) AS recent_activity;
        '''

        cursor.execute(q_metrics)
        m_row = cursor.fetchone()

        cursor.execute(q_lists)
        l_row = cursor.fetchone()

        # Parse metrics
        po_stats = m_row[0] or {}
        active_pos = int(po_stats.get('active_pos', 0))
        pending_po_value = float(po_stats.get('pending_po_value', 0.0))
        low_stock_count = int(m_row[1] or 0)
        pending_quotations = int(m_row[2] or 0)
        pending_deliveries = int(m_row[3] or 0)

        raw_ship_counts = m_row[4] or {}
        delayed_shipments = int(m_row[5] or 0)

        shipment_stats = {
            "ready_for_shipment": int(raw_ship_counts.get("Ready for Shipment", 0)),
            "dispatched": int(raw_ship_counts.get("Dispatched", 0)),
            "in_transit": int(raw_ship_counts.get("In Transit", 0)),
            "delayed": delayed_shipments,
            "delivered": int(raw_ship_counts.get("Delivered", 0)),
            "total": sum(int(v) for v in raw_ship_counts.values())
        }

        sr_counts = m_row[6] or {}
        stock_requests_overview = {
            "pending": int(sr_counts.get("Pending", 0)) + int(sr_counts.get("Open", 0)),
            "quoted": int(sr_counts.get("Quoted", 0)),
            "rejected": int(sr_counts.get("Rejected", 0)),
            "total": sum(int(v) for v in sr_counts.values())
        }

        recent_stock_movement = int(m_row[7] or 0)

        # Parse lists
        attention_items = []

        # (a) Quotations
        for q in (l_row[0] or []):
            q_id = q['quotation_id']
            q_num = q['quotation_number'] or f"QT-{q_id}"
            sup_name = q['supplier_name'] or "Registered Supplier"
            amt = float(q['total_amount']) if q['total_amount'] is not None else 0.0
            date_val = q['quotation_date']
            attention_items.append({
                "type": "quotation",
                "id": q_id,
                "reference": q_num,
                "title": f"Quotation {q_num} awaits approval",
                "description": f"Supplier: {sup_name} • Value: ₹{amt:,.2f}",
                "date": date_val,
                "status": q['status'],
                "priority": "High",
                "target_page": "quotations",
                "action_label": "Review"
            })

        # (b) Low-Stock
        for p in (l_row[1] or []):
            prod_id = p['product_id']
            avail = p['quantity_available']
            reorder = p['reorder_level'] or 10
            attention_items.append({
                "type": "low_stock",
                "id": prod_id,
                "reference": p['sku'] or f"PROD-{prod_id}",
                "title": f"Low Stock: {p['product_name']}",
                "description": f"SKU: {p['sku']} • Available: {avail} (Reorder level: {reorder})",
                "date": None,
                "status": "Low Stock",
                "priority": "Urgent" if avail == 0 else "High",
                "target_page": "stock-requests",
                "action_label": "Restock"
            })

        # (c) Deliveries
        for sh in (l_row[2] or []):
            sh_id = sh['shipment_id']
            sh_num = sh['shipment_number'] or f"SHP-{sh_id}"
            sup_name = sh['supplier_name'] or "Supplier"
            po_ref = f"PO #{sh['purchase_order_id']}" if sh['purchase_order_id'] else "N/A"
            deliv_at = sh['delivered_at']
            date_str = deliv_at[:10] if deliv_at else None
            attention_items.append({
                "type": "delivery",
                "id": sh_id,
                "reference": sh_num,
                "title": f"Shipment {sh_num} delivered, pending Stock-In",
                "description": f"{sup_name} • Order: {po_ref}",
                "date": date_str,
                "status": "Pending Stock-In",
                "priority": "High",
                "target_page": "shipments",
                "action_label": "Receive"
            })

        # Recent orders
        recent_orders = []
        for rpo in (l_row[3] or []):
            recent_orders.append({
                "purchase_order_id": rpo['purchase_order_id'],
                "order_date": rpo['order_date'],
                "expected_delivery": rpo['expected_delivery'],
                "total_amount": float(rpo['total_amount']) if rpo['total_amount'] is not None else 0.0,
                "status": rpo['status'],
                "supplier_name": rpo['supplier_name'] or "Unassigned"
            })

        # Critical low stock
        critical_low_stock = []
        for cls_row in (l_row[4] or []):
            pid = cls_row['product_id']
            qty = cls_row['quantity_available']
            critical_low_stock.append({
                "product_id": pid,
                "product_name": cls_row['product_name'],
                "sku": cls_row['sku'] or f"PROD-{pid}",
                "quantity_available": qty,
                "reorder_level": cls_row['reorder_level'] or 10,
                "status": "Out of Stock" if qty == 0 else "Low Stock"
            })

        # Recent stock requests
        recent_stock_requests = []
        for srr in (l_row[5] or []):
            recent_stock_requests.append({
                "stock_request_id": srr['stock_request_id'],
                "request_number": srr['request_number'],
                "priority": srr['priority'] or "Medium",
                "status": srr['status'],
                "required_date": srr['required_date'],
                "created_at": srr['created_at'],
                "primary_product": srr['primary_product'] or "Catalog Restock",
                "total_quantity": int(srr['total_qty']),
                "supplier_name": srr['supplier_name'] or "Open Market"
            })

        # Recent transactions
        recent_transactions = []
        for row in (l_row[6] or []):
            recent_transactions.append({
                "transaction_id": row['transaction_id'],
                "product_name": row['product_name'],
                "transaction_type": row['transaction_type'],
                "quantity": row['quantity'],
                "transaction_date": row['transaction_date']
            })

        # Recent activity
        recent_activity = []
        for act in (l_row[7] or []):
            recent_activity.append({
                "history_id": act['history_id'],
                "purchase_order_id": act['purchase_order_id'],
                "shipment_id": act['shipment_id'],
                "status": act['status'],
                "action": act['action'] or "STATUS_CHANGE",
                "notes": act['notes'] or "",
                "changed_by": act['changed_by'] or "System",
                "created_at": act['created_at']
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
    Consolidated into two optimized round-trips:
      1. Scalar metrics: Users/Roles breakdown, supplier counts, catalog valuation,
         stock transaction volume, purchase order spend, pending quotations, shipment counts,
         latest backup record, and system health status
      2. Lists: Recent purchase orders, attention items (quotations, critical low stock,
         pending POs), and recent audit log events
    Preserves all existing response keys: total_users, total_suppliers,
    total_products, total_inventory_value, recent_audits.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query 1: All scalar executive metrics and breakdowns
        q_metrics = '''
        WITH
          users_summary AS (
            SELECT json_agg(json_build_object('role_name', r.role_name, 'status', sub.status, 'count', sub.cnt)) AS data
            FROM (
              SELECT u.role_id, u.status, COUNT(*) AS cnt
              FROM "Users" u
              GROUP BY u.role_id, u.status
            ) sub
            JOIN "Roles" r ON sub.role_id = r.role_id
          ),
          suppliers_summary AS (
            SELECT COUNT(*) AS total_suppliers FROM "Suppliers"
          ),
          inventory_summary AS (
            SELECT 
                COUNT(p.product_id) as total_products,
                COALESCE(SUM(i.quantity_available), 0) as total_units,
                COALESCE(SUM(p.selling_price * i.quantity_available), 0) as total_inventory_value,
                COUNT(CASE WHEN i.quantity_available <= p.reorder_level THEN 1 END) as low_stock_count,
                COUNT(CASE WHEN i.quantity_available = 0 THEN 1 END) as out_of_stock_count
            FROM "Products" p
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
          ),
          stock_tx_summary AS (
            SELECT 
                COALESCE(SUM(CASE WHEN transaction_type = 'STOCK_IN' THEN quantity ELSE 0 END), 0) as received_units,
                COALESCE(SUM(CASE WHEN transaction_type = 'STOCK_OUT' THEN quantity ELSE 0 END), 0) as issued_units,
                COUNT(*) as total_transactions
            FROM "StockTransactions"
          ),
          po_summary AS (
            SELECT json_agg(json_build_object('status', status, 'count', cnt, 'val', val)) AS data
            FROM (
              SELECT status, COUNT(*) AS cnt, COALESCE(SUM(total_amount), 0) AS val
              FROM "PurchaseOrders"
              GROUP BY status
            ) po_sub
          ),
          quotations_summary AS (
            SELECT COUNT(*) AS pending_quotations_count
            FROM "SupplierQuotations"
            WHERE status IN ('Submitted', 'Pending', 'Under Review')
          ),
          shipment_summary AS (
            SELECT 
                COUNT(CASE WHEN status = 'Ready for Shipment' THEN 1 END) as ready,
                COUNT(CASE WHEN status IN ('Dispatched', 'In Transit') THEN 1 END) as in_transit,
                COUNT(CASE WHEN status = 'Delivered' THEN 1 END) as delivered,
                COUNT(*) as total
            FROM "Shipments"
          ),
          backup_summary AS (
            SELECT backup_id, backup_name, backup_type, backup_date, backup_size, status
            FROM "BackupHistory"
            ORDER BY backup_id DESC LIMIT 1
          ),
          status_summary AS (
            SELECT status_id, module_name, status, progress, message, updated_at
            FROM "SystemStatus"
            ORDER BY status_id ASC LIMIT 1
          )
        SELECT 
          (SELECT data FROM users_summary) AS users_breakdown,
          (SELECT total_suppliers FROM suppliers_summary) AS total_suppliers,
          (SELECT row_to_json(inventory_summary.*) FROM inventory_summary) AS inventory_health,
          (SELECT row_to_json(stock_tx_summary.*) FROM stock_tx_summary) AS stock_tx_health,
          (SELECT data FROM po_summary) AS po_breakdown,
          (SELECT pending_quotations_count FROM quotations_summary) AS pending_quotations_count,
          (SELECT row_to_json(shipment_summary.*) FROM shipment_summary) AS shipment_stats,
          (SELECT row_to_json(backup_summary.*) FROM backup_summary) AS latest_backup,
          (SELECT row_to_json(status_summary.*) FROM status_summary) AS system_status;
        '''

        # Query 2: All recent lists and attention items
        q_lists = '''
        SELECT
          -- Recent purchase orders (limit 5)
          (SELECT json_agg(po_row) FROM (
             SELECT po.purchase_order_id, s.supplier_name, po.order_date, po.expected_delivery, po.total_amount, po.status 
             FROM "PurchaseOrders" po 
             LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id 
             ORDER BY po.order_date DESC NULLS LAST, po.purchase_order_id DESC 
             LIMIT 5
           ) po_row) AS recent_orders,

          -- Attention quotations (limit 4)
          (SELECT json_agg(q_row) FROM (
             SELECT sq.quotation_id, sq.quotation_number, s.supplier_name, p.product_name, sq.total_amount, sq.status, sq.quotation_date
             FROM "SupplierQuotations" sq
             LEFT JOIN "Suppliers" s ON sq.supplier_id = s.supplier_id
             LEFT JOIN "Products" p ON sq.product_id = p.product_id
             WHERE sq.status IN ('Submitted', 'Pending', 'Under Review')
             ORDER BY sq.quotation_date DESC NULLS LAST, sq.quotation_id DESC
             LIMIT 4
           ) q_row) AS attention_quotations,

          -- Attention low-stock (limit 3)
          (SELECT json_agg(ls_row) FROM (
             SELECT p.product_id, p.product_name, p.sku, i.quantity_available, p.reorder_level
             FROM "Products" p
             JOIN "Inventory" i ON p.product_id = i.product_id
             WHERE i.quantity_available <= p.reorder_level
             ORDER BY i.quantity_available ASC
             LIMIT 3
           ) ls_row) AS attention_low_stock,

          -- Attention pending purchase orders (limit 3)
          (SELECT json_agg(ppo_row) FROM (
             SELECT po.purchase_order_id, s.supplier_name, po.total_amount, po.status, po.order_date
             FROM "PurchaseOrders" po
             LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
             WHERE po.status = 'Pending'
             ORDER BY po.order_date DESC NULLS LAST, po.purchase_order_id DESC
             LIMIT 3
           ) ppo_row) AS attention_pending_pos,

          -- Recent audit logs (limit 5)
          (SELECT json_agg(aud_row) FROM (
             SELECT al.log_id, al.action, COALESCE(u.username, 'System') AS username, al.action_time, al.table_name, al.record_id, al.ip_address
             FROM "AuditLogs" al
             LEFT JOIN "Users" u ON al.user_id = u.user_id
             ORDER BY al.action_time DESC
             LIMIT 5
           ) aud_row) AS recent_audits;
        '''

        cursor.execute(q_metrics)
        m_row = cursor.fetchone()

        cursor.execute(q_lists)
        l_row = cursor.fetchone()

        # 1. Users Breakdown
        total_users = 0
        active_users_count = 0
        inactive_users_count = 0
        users_by_role = {}
        for item in (m_row[0] or []):
            role_name = item['role_name']
            status = item['status']
            count = int(item['count'])
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

        # 2. Total Suppliers
        total_suppliers = int(m_row[1] or 0)

        # 3. Product Catalog & Inventory Health
        inv_data = m_row[2] or {}
        total_products = int(inv_data.get('total_products', 0))
        total_units = int(inv_data.get('total_units', 0))
        total_inventory_value = float(inv_data.get('total_inventory_value', 0.0))
        low_stock_count = int(inv_data.get('low_stock_count', 0))
        out_of_stock_count = int(inv_data.get('out_of_stock_count', 0))

        # 4. Stock Movement Throughput
        tx_data = m_row[3] or {}
        received_units = int(tx_data.get('received_units', 0))
        issued_units = int(tx_data.get('issued_units', 0))
        total_transactions = int(tx_data.get('total_transactions', 0))

        # 5. Purchase Orders & Spend Breakdown
        active_pos_count = 0
        active_pos_value = 0.0
        po_status_breakdown = {}
        total_pos_count = 0
        for item in (m_row[4] or []):
            status_val = item['status']
            count = int(item['count'])
            val = float(item['val'] or 0.0)
            total_pos_count += count
            po_status_breakdown[status_val] = {
                "count": count,
                "value": val
            }
            if status_val in ('Pending', 'Accepted'):
                active_pos_count += count
                active_pos_value += val

        # 6. Pending Quotations Overview
        pending_quotations_count = int(m_row[5] or 0)

        # 7. Shipment & Logistics Statistics
        ship_data = m_row[6] or {}
        shipment_stats = {
            "ready_for_shipment": int(ship_data.get('ready', 0)),
            "in_transit": int(ship_data.get('in_transit', 0)),
            "delivered": int(ship_data.get('delivered', 0)),
            "total_shipments": int(ship_data.get('total', 0))
        }

        # 8. Latest Database Backup
        bk_row = m_row[7]
        latest_backup = None
        if bk_row:
            latest_backup = {
                "backup_id": bk_row['backup_id'],
                "backup_name": bk_row['backup_name'],
                "backup_type": bk_row['backup_type'],
                "backup_date": bk_row['backup_date'],
                "backup_size": bk_row['backup_size'],
                "status": bk_row['status']
            }

        # 9. System Health Summary
        sys_row = m_row[8]
        system_status = None
        if sys_row:
            system_status = {
                "module_name": sys_row['module_name'],
                "status": sys_row['status'],
                "progress": sys_row['progress'],
                "message": sys_row['message'],
                "updated_at": sys_row['updated_at']
            }

        # 10. Recent Purchase Orders
        recent_orders = []
        for r in (l_row[0] or []):
            recent_orders.append({
                "purchase_order_id": r['purchase_order_id'],
                "supplier_name": r['supplier_name'] or "Unknown Supplier",
                "order_date": r['order_date'],
                "expected_delivery": r['expected_delivery'],
                "total_amount": float(r['total_amount'] or 0.0),
                "status": r['status']
            })

        # 11. Needs Your Attention Items
        attention_items = []

        # A. Pending Quotations
        for q_row in (l_row[1] or []):
            q_id = q_row['quotation_id']
            q_num = q_row['quotation_number'] or f"QTN-{q_id:04d}"
            s_name = q_row['supplier_name'] or "Supplier"
            p_name = q_row['product_name'] or "Product"
            amt = float(q_row['total_amount'] or 0.0)
            attention_items.append({
                "type": "quotation",
                "id": q_id,
                "title": f"Quotation {q_num} ({s_name})",
                "subtitle": f"{p_name} — Total: ₹{amt:,.2f}",
                "status": q_row['status'],
                "badge": "Awaiting Approval",
                "badge_color": "warning",
                "action_label": "Review →",
                "action_route": "quotations"
            })

        # B. Critical Low Stock Products
        for p_row in (l_row[2] or []):
            prod_id = p_row['product_id']
            prod_name = p_row['product_name']
            sku = p_row['sku']
            qty = p_row['quantity_available']
            reorder = p_row['reorder_level']
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
        for po_item in (l_row[3] or []):
            po_id = po_item['purchase_order_id']
            s_name = po_item['supplier_name'] or "Supplier"
            po_amt = float(po_item['total_amount'] or 0.0)
            attention_items.append({
                "type": "purchase_order",
                "id": po_id,
                "title": f"Purchase Order #{po_id:04d} ({s_name})",
                "subtitle": f"Value: ₹{po_amt:,.2f} — Waiting for supplier response",
                "status": po_item['status'],
                "badge": "Pending Response",
                "badge_color": "info",
                "action_label": "View →",
                "action_route": "purchase-orders"
            })

        # 12. Recent System Audit Logs
        recent_audits = []
        for row in (l_row[4] or []):
            action = row['action'] or "Action"
            username = row['username']
            action_time = row['action_time']
            table_name = row['table_name'] or "System"
            record_id = row['record_id']
            ip_address = row['ip_address']

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
                "log_id": row['log_id'],
                "action": readable_action,
                "username": username,
                "timestamp": action_time,
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