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


def get_supplier_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Total purchase orders
        cursor.execute('SELECT COUNT(*) FROM "PurchaseOrders"')
        total_purchase_orders = cursor.fetchone()[0]

        # Received orders
        cursor.execute('''
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE status = 'Received'
        ''')
        received_orders = cursor.fetchone()[0]

        # Completed orders
        cursor.execute('''
            SELECT COUNT(*)
            FROM "PurchaseOrders"
            WHERE status = 'Completed'
        ''')
        completed_orders = cursor.fetchone()[0]

        # Total purchase amount
        cursor.execute('''
            SELECT COALESCE(SUM(total_amount), 0)
            FROM "PurchaseOrders"
        ''')
        total_purchase_amount = cursor.fetchone()[0]

        # Total quotations
        cursor.execute('SELECT COUNT(*) FROM "SupplierQuotations"')
        total_quotations = cursor.fetchone()[0]

        # Pending quotations
        cursor.execute('''
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE status = 'Pending'
        ''')
        pending_quotations = cursor.fetchone()[0]

        # Approved quotations
        cursor.execute('''
            SELECT COUNT(*)
            FROM "SupplierQuotations"
            WHERE status = 'Approved'
        ''')
        approved_quotations = cursor.fetchone()[0]

        return {
            "total_purchase_orders": total_purchase_orders,
            "received_orders": received_orders,
            "completed_orders": completed_orders,
            "total_purchase_amount": float(total_purchase_amount),
            "total_quotations": total_quotations,
            "pending_quotations": pending_quotations,
            "approved_quotations": approved_quotations
        }

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