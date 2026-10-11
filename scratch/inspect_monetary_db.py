import sys
import os

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.team3.report_service import get_db_connection

def inspect_monetary():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("=== PRODUCTS ===")
    cur.execute('SELECT * FROM "Products" LIMIT 1')
    colnames = [desc[0] for desc in cur.description]
    print("  Products columns:", colnames)
    row = cur.fetchone()
    print("  Products sample row:", row)

    print("\n=== PURCHASE ORDERS ===")
    cur.execute('SELECT purchase_order_id, total_amount, order_date FROM "PurchaseOrders" LIMIT 5')
    for row in cur.fetchall():
        print(f"  PO #{row[0]}: Total: {row[1]}, Date: {row[2]}")

    print("\n=== PURCHASE ORDER ITEMS ===")
    cur.execute('SELECT * FROM "PurchaseOrderItems" LIMIT 1')
    print("  PO Items columns:", [desc[0] for desc in cur.description])
    print("  PO Items row:", cur.fetchone())

    print("\n=== SUPPLIER QUOTATIONS ===")
    cur.execute('SELECT * FROM "SupplierQuotations" LIMIT 1')
    print("  Quotations columns:", [desc[0] for desc in cur.description])
    print("  Quotations row:", cur.fetchone())

    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect_monetary()
