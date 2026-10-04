import os, psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

for sup_id, name in [(5, 'Demo Supplier'), (4, 'Supplier 1')]:
    print(f"\n=== ATTENTION ITEMS FOR {name} (ID: {sup_id}) ===")
    
    # 1. Stock Requests
    cur.execute("""
        SELECT stock_request_id, request_number, priority, required_date
        FROM "StockRequests"
        WHERE supplier_id = %s AND status IN ('Pending', 'Open')
    """, (sup_id,))
    srs = cur.fetchall()
    print("Pending Stock Requests:", srs)

    # 2. POs awaiting acceptance
    cur.execute("""
        SELECT purchase_order_id, order_date, total_amount, status, supplier_response
        FROM "PurchaseOrders"
        WHERE supplier_id = %s AND (supplier_response = 'Pending' OR supplier_response IS NULL) AND status NOT IN ('Cancelled', 'Rejected', 'Delivered')
    """, (sup_id,))
    pos = cur.fetchall()
    print("POs awaiting acceptance:", pos)

    # 3. Delayed Shipments
    cur.execute("""
        SELECT shipment_id, shipment_number, expected_delivery, status
        FROM "Shipments"
        WHERE supplier_id = %s AND status NOT IN ('Delivered', 'Cancelled') AND expected_delivery < CURRENT_DATE
    """, (sup_id,))
    delayed = cur.fetchall()
    print("Delayed Shipments:", delayed)

cur.close()
conn.close()
