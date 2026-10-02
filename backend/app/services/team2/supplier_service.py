from app.extensions import get_db_connection
from psycopg2 import Error

def get_supplier_dashboard_stats(supplier_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM "PurchaseOrders"
            WHERE supplier_id = %s
        ''', (supplier_id,))
        total_orders = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM "PurchaseOrders"
            WHERE supplier_id = %s AND status = 'Delivered'
        ''', (supplier_id,))
        delivered_orders = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM "PurchaseOrders"
            WHERE supplier_id = %s AND status = 'Pending'
        ''', (supplier_id,))
        pending_orders = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT purchase_order_id, status, total_amount
            FROM "PurchaseOrders"
            WHERE supplier_id = %s
            ORDER BY order_date DESC LIMIT 5
        ''', (supplier_id,))
        
        recent_orders = []
        for r in cursor.fetchall():
            recent_orders.append({
                'order_id': r[0],
                'status': r[1],
                'total_amount': float(r[2]) if r[2] else 0.0
            })
            
        return {
            'total_orders': total_orders,
            'delivered_orders': delivered_orders,
            'pending_orders': pending_orders,
            'recent_orders': recent_orders
        }, None
        
    except Error as e:
        print("DB ERROR in get_supplier_dashboard_stats:", e)
        return None, "Database error"
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
