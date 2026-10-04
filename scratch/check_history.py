import os, psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT history_id, purchase_order_id, shipment_id, status, previous_status, action, notes, changed_by, created_at
    FROM "OrderStatusHistory"
    WHERE supplier_id = 5 OR supplier_id = 4
    ORDER BY created_at DESC
    LIMIT 5
""")
print("Supplier History rows:")
for r in cur.fetchall():
    print(" ", r)

cur.execute("""
    SELECT status, COUNT(*)
    FROM "Shipments"
    WHERE supplier_id = 5
    GROUP BY status
""")
print("\nShipment counts for supplier 5:", cur.fetchall())

cur.execute("""
    SELECT COUNT(*)
    FROM "Shipments"
    WHERE supplier_id = 5 AND status NOT IN ('Delivered', 'Cancelled')
""")
print("\nPending deliveries for supplier 5:", cur.fetchone()[0])

cur.close()
conn.close()
