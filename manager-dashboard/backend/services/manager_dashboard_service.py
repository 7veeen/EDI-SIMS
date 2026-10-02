from extensions import get_db_connection, release_db_connection, table_exists
import psycopg2
from psycopg2.extras import RealDictCursor


def safe_query_scalar(cur, query, params=None, default=0):
    """Executes a scalar query safely, returning default if table or record missing."""
    try:
        cur.execute(query, params or ())
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception as e:
        return default


def get_dashboard_summary():
    """
    Calculates summary metrics dynamically from real Supabase PostgreSQL:
    - total_products
    - low_stock_products
    - out_of_stock_products
    - pending_stock_requests
    - pending_quotations
    - pending_purchase_orders
    - orders_in_transit
    - total_employees
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # 1. Total Products
        total_products = safe_query_scalar(cur, 'SELECT COUNT(*) FROM "Products"')

        # 2. Low Stock Products (quantity_available <= reorder_level AND quantity_available > 0)
        low_stock = safe_query_scalar(
            cur,
            '''
            SELECT COUNT(*)
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0
            '''
        )

        # 3. Out of Stock Products
        out_of_stock = safe_query_scalar(
            cur,
            '''
            SELECT COUNT(*)
            FROM "Inventory"
            WHERE quantity_available = 0
            '''
        )

        # 4. Pending Stock Requests (Check if StockRequests table exists)
        stock_requests_table = table_exists(cur, "StockRequests")
        if stock_requests_table:
            pending_stock_requests = safe_query_scalar(
                cur,
                f'SELECT COUNT(*) FROM "{stock_requests_table}" WHERE status ILIKE %s',
                ('Pending',)
            )
        else:
            pending_stock_requests = 0

        # 5. Pending Quotations
        quotations_table = table_exists(cur, "SupplierQuotations") or table_exists(cur, "Quotations")
        if quotations_table:
            pending_quotations = safe_query_scalar(
                cur,
                f'SELECT COUNT(*) FROM "{quotations_table}" WHERE status ILIKE %s',
                ('Pending',)
            )
        else:
            pending_quotations = 0

        # 6. Pending Purchase Orders
        po_table = table_exists(cur, "PurchaseOrders")
        if po_table:
            pending_pos = safe_query_scalar(
                cur,
                f'SELECT COUNT(*) FROM "{po_table}" WHERE status ILIKE %s',
                ('Pending',)
            )
            # 7. Orders in Transit
            orders_in_transit = safe_query_scalar(
                cur,
                f'''
                SELECT COUNT(*) FROM "{po_table}" 
                WHERE status ILIKE 'Shipped' OR status ILIKE 'In Transit' OR status ILIKE 'Accepted'
                '''
            )
        else:
            pending_pos = 0
            orders_in_transit = 0

        # 8. Total Active Employees
        total_employees = safe_query_scalar(
            cur,
            '''
            SELECT COUNT(*)
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE r.role_name = 'Employee' AND u.status = 'Active'
            '''
        )

        return {
            "total_products": int(total_products),
            "low_stock_products": int(low_stock),
            "out_of_stock_products": int(out_of_stock),
            "pending_stock_requests": int(pending_stock_requests),
            "pending_quotations": int(pending_quotations),
            "pending_purchase_orders": int(pending_pos),
            "orders_in_transit": int(orders_in_transit),
            "total_employees": int(total_employees)
        }
    finally:
        cur.close()
        release_db_connection(conn)


def get_inventory_overview():
    """
    Returns live inventory breakdown and category distribution.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Status breakdown
        cur.execute('''
            SELECT 
                COUNT(*) FILTER (WHERE i.quantity_available > p.reorder_level) AS in_stock,
                COUNT(*) FILTER (WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0) AS low_stock,
                COUNT(*) FILTER (WHERE i.quantity_available = 0) AS out_of_stock,
                COALESCE(SUM(i.quantity_available), 0) AS total_units
            FROM "Products" p
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
        ''')
        row = cur.fetchone()
        in_stock = row[0] or 0
        low_stock = row[1] or 0
        out_of_stock = row[2] or 0
        total_units = row[3] or 0

        # Category breakdown
        category_breakdown = []
        try:
            cur.execute('''
                SELECT 
                    c.category_id,
                    c.category_name,
                    COUNT(p.product_id) AS product_count,
                    COALESCE(SUM(i.quantity_available), 0) AS total_stock
                FROM "Categories" c
                LEFT JOIN "Products" p ON c.category_id = p.category_id
                LEFT JOIN "Inventory" i ON p.product_id = i.product_id
                GROUP BY c.category_id, c.category_name
                ORDER BY product_count DESC
            ''')
            cat_rows = cur.fetchall()
            for r in cat_rows:
                category_breakdown.append({
                    "category_id": r[0],
                    "category_name": r[1],
                    "product_count": r[2],
                    "total_stock": int(r[3])
                })
        except Exception:
            pass

        return {
            "status_breakdown": {
                "in_stock": int(in_stock),
                "low_stock": int(low_stock),
                "out_of_stock": int(out_of_stock),
                "total_units": int(total_units)
            },
            "category_breakdown": category_breakdown
        }
    finally:
        cur.close()
        release_db_connection(conn)


def get_procurement_overview():
    """
    Pipeline funnel counts:
    Stock Requests -> Quotations -> Purchase Orders -> Accepted -> Shipped -> Delivered
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Stock Requests count
        req_table = table_exists(cur, "StockRequests")
        total_stock_requests = safe_query_scalar(cur, f'SELECT COUNT(*) FROM "{req_table}"') if req_table else 0
        pending_stock_requests = safe_query_scalar(cur, f'SELECT COUNT(*) FROM "{req_table}" WHERE status ILIKE %s', ('Pending',)) if req_table else 0

        # Quotations count
        quo_table = table_exists(cur, "SupplierQuotations") or table_exists(cur, "Quotations")
        total_quotations = safe_query_scalar(cur, f'SELECT COUNT(*) FROM "{quo_table}"') if quo_table else 0
        pending_quotations = safe_query_scalar(cur, f'SELECT COUNT(*) FROM "{quo_table}" WHERE status ILIKE %s', ('Pending',)) if quo_table else 0
        approved_quotations = safe_query_scalar(cur, f'SELECT COUNT(*) FROM "{quo_table}" WHERE status ILIKE %s', ('Approved',)) if quo_table else 0

        # Purchase Orders by status
        po_table = table_exists(cur, "PurchaseOrders")
        po_stats = {
            "total": 0,
            "pending": 0,
            "accepted": 0,
            "shipped": 0,
            "delivered": 0,
            "completed": 0
        }
        if po_table:
            cur.execute(f'''
                SELECT 
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status ILIKE 'Pending') AS pending,
                    COUNT(*) FILTER (WHERE status ILIKE 'Accepted') AS accepted,
                    COUNT(*) FILTER (WHERE status ILIKE 'Shipped' OR status ILIKE 'In Transit') AS shipped,
                    COUNT(*) FILTER (WHERE status ILIKE 'Delivered' OR status ILIKE 'Received') AS delivered,
                    COUNT(*) FILTER (WHERE status ILIKE 'Completed') AS completed
                FROM "{po_table}"
            ''')
            row = cur.fetchone()
            if row:
                po_stats = {
                    "total": int(row[0] or 0),
                    "pending": int(row[1] or 0),
                    "accepted": int(row[2] or 0),
                    "shipped": int(row[3] or 0),
                    "delivered": int(row[4] or 0),
                    "completed": int(row[5] or 0)
                }

        return {
            "stock_requests": {
                "total": int(total_stock_requests),
                "pending": int(pending_stock_requests)
            },
            "quotations": {
                "total": int(total_quotations),
                "pending": int(pending_quotations),
                "approved": int(approved_quotations)
            },
            "purchase_orders": po_stats
        }
    finally:
        cur.close()
        release_db_connection(conn)


def get_pending_actions():
    """
    Returns prioritized list of tasks requiring Manager attention:
    - Low-stock items
    - Pending quotations
    - Pending purchase orders
    """
    conn = get_db_connection()
    cur = conn.cursor()
    actions = []
    try:
        # 1. Low stock alerts
        try:
            cur.execute('''
                SELECT p.product_id, p.product_name, i.quantity_available, p.reorder_level
                FROM "Products" p
                JOIN "Inventory" i ON p.product_id = i.product_id
                WHERE i.quantity_available <= p.reorder_level
                ORDER BY i.quantity_available ASC
                LIMIT 5
            ''')
            for r in cur.fetchall():
                actions.append({
                    "type": "LOW_STOCK",
                    "severity": "high" if r[2] == 0 else "medium",
                    "title": f"Stock Alert: {r[1]}",
                    "description": f"Current stock is {r[2]} (Reorder level: {r[3]}). Reorder required.",
                    "reference_id": r[0],
                    "action_label": "Create Stock Request",
                    "action_target": "stock-requests"
                })
        except Exception:
            pass

        # 2. Pending quotations
        quo_table = table_exists(cur, "SupplierQuotations") or table_exists(cur, "Quotations")
        if quo_table:
            try:
                cur.execute(f'''
                    SELECT quotation_id, supplier_id, (quoted_price * quantity) AS total_amount, quotation_date
                    FROM "{quo_table}"
                    WHERE status ILIKE 'Pending'
                    ORDER BY quotation_id DESC
                    LIMIT 5
                ''')
                for r in cur.fetchall():
                    actions.append({
                        "type": "PENDING_QUOTATION",
                        "severity": "medium",
                        "title": f"Quotation #{r[0]} Awaiting Approval",
                        "description": f"Supplier #{r[1]} submitted quotation for INR {float(r[2] or 0):,.2f}.",
                        "reference_id": r[0],
                        "action_label": "Review Quotation",
                        "action_target": "quotations"
                    })
            except Exception:
                pass

        # 3. Pending Purchase Orders
        po_table = table_exists(cur, "PurchaseOrders")
        if po_table:
            try:
                cur.execute(f'''
                    SELECT purchase_order_id, supplier_id, total_amount, status
                    FROM "{po_table}"
                    WHERE status ILIKE 'Pending'
                    ORDER BY purchase_order_id DESC
                    LIMIT 5
                ''')
                for r in cur.fetchall():
                    actions.append({
                        "type": "PENDING_PO",
                        "severity": "high",
                        "title": f"Purchase Order #{r[0]} Pending",
                        "description": f"PO of INR {float(r[2] or 0):,.2f} needs approval or dispatch.",
                        "reference_id": r[0],
                        "action_label": "Manage PO",
                        "action_target": "purchase-orders"
                    })
            except Exception:
                pass

        return actions
    finally:
        cur.close()
        release_db_connection(conn)


def get_low_stock_products():
    """
    Returns real products where quantity_available <= reorder_level.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                COALESCE(c.category_name, 'Unassigned') AS category_name,
                i.quantity_available,
                p.reorder_level,
                p.status,
                i.last_updated
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            LEFT JOIN "Categories" c ON p.category_id = c.category_id
            WHERE i.quantity_available <= p.reorder_level
            ORDER BY i.quantity_available ASC, p.product_name ASC
        ''')
        rows = cur.fetchall()
        items = []
        for r in rows:
            qty = r[4]
            reorder = r[5]
            stock_status = "OUT OF STOCK" if qty == 0 else "CRITICAL LOW" if qty <= (reorder / 2) else "LOW STOCK"
            items.append({
                "product_id": r[0],
                "product_name": r[1],
                "sku": r[2],
                "category_name": r[3],
                "quantity_available": qty,
                "reorder_level": reorder,
                "product_status": r[6],
                "stock_status": stock_status,
                "last_updated": r[7].isoformat() if r[7] else None
            })
        return items
    finally:
        cur.close()
        release_db_connection(conn)


def get_recent_purchase_orders(limit=10):
    """
    Returns latest Purchase Orders from Supabase.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    po_table = table_exists(cur, "PurchaseOrders")
    if not po_table:
        cur.close()
        release_db_connection(conn)
        return []

    try:
        sup_table = table_exists(cur, "Suppliers")
        if sup_table:
            query = f'''
                SELECT 
                    po.purchase_order_id,
                    COALESCE(s.supplier_name, 'Supplier #' || po.supplier_id::text) AS supplier_name,
                    po.total_amount,
                    po.status,
                    po.order_date
                FROM "{po_table}" po
                LEFT JOIN "{sup_table}" s ON po.supplier_id = s.supplier_id
                ORDER BY po.purchase_order_id DESC
                LIMIT %s
            '''
        else:
            query = f'''
                SELECT 
                    purchase_order_id,
                    'Supplier #' || supplier_id::text AS supplier_name,
                    total_amount,
                    status,
                    order_date
                FROM "{po_table}"
                ORDER BY purchase_order_id DESC
                LIMIT %s
            '''

        cur.execute(query, (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            results.append({
                "po_id": r[0],
                "supplier_name": r[1],
                "total_amount": float(r[2] or 0),
                "status": r[3],
                "created_at": r[4].isoformat() if r[4] else None
            })
        return results
    finally:
        cur.close()
        release_db_connection(conn)


def get_recent_stock_transactions(limit=10):
    """
    Returns latest stock transactions (STOCK_IN, STOCK_OUT, etc.)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    tx_table = table_exists(cur, "StockTransactions")
    if not tx_table:
        cur.close()
        release_db_connection(conn)
        return []

    try:
        cur.execute(f'''
            SELECT 
                st.transaction_id,
                COALESCE(p.product_name, 'Product #' || st.product_id::text) AS product_name,
                st.transaction_type,
                st.quantity,
                COALESCE(u.username, 'System') AS user_name,
                st.transaction_date
            FROM "{tx_table}" st
            LEFT JOIN "Products" p ON st.product_id = p.product_id
            LEFT JOIN "Users" u ON st.user_id = u.user_id
            ORDER BY st.transaction_id DESC
            LIMIT %s
        ''', (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            results.append({
                "transaction_id": r[0],
                "product_name": r[1],
                "transaction_type": r[2],
                "quantity": r[3],
                "performed_by": r[4],
                "transaction_date": r[5].isoformat() if r[5] else None
            })
        return results
    finally:
        cur.close()
        release_db_connection(conn)


def get_employee_overview():
    """
    Employee metrics and roster preview for Manager.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                COUNT(*) AS total_employees,
                COUNT(*) FILTER (WHERE u.status = 'Active') AS active_employees
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE r.role_name = 'Employee'
        ''')
        row = cur.fetchone()
        total = row[0] or 0
        active = row[1] or 0

        # Roster list
        cur.execute('''
            SELECT u.user_id, u.username, u.email, u.status
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE r.role_name = 'Employee'
            ORDER BY u.user_id ASC
            LIMIT 10
        ''')
        roster = []
        for r in cur.fetchall():
            roster.append({
                "user_id": r[0],
                "username": r[1],
                "email": r[2],
                "status": r[3]
            })

        return {
            "total_employees": total,
            "active_employees": active,
            "employees": roster
        }
    finally:
        cur.close()
        release_db_connection(conn)


def get_supplier_overview():
    """
    Supplier counts and directory preview for Manager.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        sup_table = table_exists(cur, "Suppliers")
        if not sup_table:
            return {
                "total_suppliers": 0,
                "active_suppliers": 0,
                "suppliers": []
            }

        cur.execute(f'''
            SELECT 
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status ILIKE 'Active') AS active
            FROM "{sup_table}"
        ''')
        row = cur.fetchone()
        total = row[0] or 0
        active = row[1] or 0

        cur.execute(f'''
            SELECT supplier_id, supplier_name, status, COALESCE(phone, email, contact_person) AS contact_info
            FROM "{sup_table}"
            ORDER BY supplier_id ASC
            LIMIT 10
        ''')
        suppliers = []
        for r in cur.fetchall():
            suppliers.append({
                "supplier_id": r[0],
                "supplier_name": r[1],
                "status": r[2],
                "contact_info": r[3]
            })

        return {
            "total_suppliers": total,
            "active_suppliers": active,
            "suppliers": suppliers
        }
    finally:
        cur.close()
        release_db_connection(conn)


def get_manager_notifications(limit=10):
    """
    Retrieves latest system notifications and unread count.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    notif_table = table_exists(cur, "Notifications")
    if not notif_table:
        cur.close()
        release_db_connection(conn)
        return {"unread_count": 0, "notifications": []}

    try:
        cur.execute(f'''
            SELECT COUNT(*)
            FROM "{notif_table}"
            WHERE is_read = FALSE
        ''')
        unread_count = cur.fetchone()[0] or 0

        cur.execute(f'''
            SELECT 
                notification_id,
                title,
                message,
                notification_type,
                is_read,
                created_at
            FROM "{notif_table}"
            ORDER BY notification_id DESC
            LIMIT %s
        ''', (limit,))
        notifications = []
        for r in cur.fetchall():
            notifications.append({
                "notification_id": r[0],
                "title": r[1],
                "message": r[2],
                "notification_type": r[3],
                "is_read": r[4],
                "created_at": r[5].isoformat() if r[5] else None
            })

        return {
            "unread_count": unread_count,
            "notifications": notifications
        }
    finally:
        cur.close()
        release_db_connection(conn)


def mark_notification_read(notification_id):
    """
    Marks a notification as read.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    notif_table = table_exists(cur, "Notifications")
    if not notif_table:
        cur.close()
        release_db_connection(conn)
        return False, "Notifications table not found"

    try:
        cur.execute(f'''
            UPDATE "{notif_table}"
            SET is_read = TRUE
            WHERE notification_id = %s
            RETURNING notification_id, is_read
        ''', (notification_id,))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return False, "Notification not found"
        return True, None
    finally:
        cur.close()
        release_db_connection(conn)

