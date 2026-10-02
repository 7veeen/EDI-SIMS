from app.extensions import get_db_connection
from psycopg2 import Error

def get_supplier_purchase_orders(supplier_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT po.purchase_order_id, po.order_date, po.expected_delivery, po.status, po.total_amount,
                   poi.quantity, p.product_name, p.sku, p.product_id
            FROM "PurchaseOrders" po
            JOIN "PurchaseOrderItems" poi ON po.purchase_order_id = poi.purchase_order_id
            JOIN "Products" p ON poi.product_id = p.product_id
            WHERE po.supplier_id = %s
            ORDER BY po.order_date DESC
        ''', (supplier_id,))
        
        rows = cursor.fetchall()
        orders = []
        for r in rows:
            orders.append({
                'purchase_order_id': r[0],
                'order_date': r[1].isoformat() if r[1] else None,
                'expected_delivery': r[2].isoformat() if r[2] else None,
                'status': r[3],
                'total_amount': float(r[4]) if r[4] else 0.0,
                'quantity': r[5],
                'product_name': r[6],
                'sku': r[7],
                'product_id': r[8]
            })
        return orders, None
    except Error as e:
        print("DB ERROR in get_supplier_purchase_orders:", e)
        return None, "Database error"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_all_purchase_orders():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT po.purchase_order_id, po.order_date, po.expected_delivery, po.status, po.total_amount,
                   s.supplier_name
            FROM "PurchaseOrders" po
            JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
            ORDER BY po.order_date DESC
        ''')
        
        rows = cursor.fetchall()
        orders = []
        for r in rows:
            orders.append({
                'purchase_order_id': r[0],
                'order_date': r[1].isoformat() if r[1] else None,
                'expected_delivery': r[2].isoformat() if r[2] else None,
                'status': r[3],
                'total_amount': float(r[4]) if r[4] else 0.0,
                'supplier_name': r[5]
            })
        return orders, None
    except Error as e:
        print("DB ERROR in get_all_purchase_orders:", e)
        return None, "Database error"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_purchase_order_status(po_id, status, supplier_id=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if supplier_id:
            cursor.execute('''
                UPDATE "PurchaseOrders"
                SET status = %s
                WHERE purchase_order_id = %s AND supplier_id = %s
                RETURNING purchase_order_id
            ''', (status, po_id, supplier_id))
        else:
            cursor.execute('''
                UPDATE "PurchaseOrders"
                SET status = %s
                WHERE purchase_order_id = %s
                RETURNING purchase_order_id
            ''', (status, po_id))
            
        if not cursor.fetchone():
            return False, "Purchase Order not found or permission denied"
            
        conn.commit()
        return True, None
    except Error as e:
        print("DB ERROR in update_purchase_order_status:", e)
        return False, "Database error"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
