import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

print("=== 1. SUPPLIERS ===")
cur.execute('SELECT supplier_id, supplier_name, status FROM "Suppliers";')
for r in cur.fetchall():
    print(r)

print("\n=== 2. POs per supplier ===")
cur.execute('''
    SELECT supplier_id, status, supplier_response, COUNT(*), SUM(total_amount)
    FROM "PurchaseOrders"
    GROUP BY supplier_id, status, supplier_response
    ORDER BY supplier_id, status;
''')
for r in cur.fetchall():
    print(r)

print("\n=== 3. QUOTATIONS per supplier ===")
cur.execute('''
    SELECT supplier_id, status, COUNT(*), SUM(COALESCE(total_amount, quoted_price * quantity))
    FROM "SupplierQuotations"
    GROUP BY supplier_id, status
    ORDER BY supplier_id, status;
''')
for r in cur.fetchall():
    print(r)

print("\n=== 4. SHIPMENTS per supplier ===")
cur.execute('''
    SELECT supplier_id, status, 
           COUNT(*),
           COUNT(CASE WHEN expected_delivery IS NOT NULL AND delivered_at IS NOT NULL THEN 1 END) as comparable_dates,
           COUNT(CASE WHEN expected_delivery IS NOT NULL AND delivered_at IS NOT NULL AND delivered_at::date <= expected_delivery THEN 1 END) as on_time,
           COUNT(CASE WHEN expected_delivery IS NOT NULL AND delivered_at IS NOT NULL AND delivered_at::date > expected_delivery THEN 1 END) as late
    FROM "Shipments"
    GROUP BY supplier_id, status
    ORDER BY supplier_id, status;
''')
for r in cur.fetchall():
    print(r)

print("\n=== 5. CHECK DELIVERY DELAY (DAYS) ===")
cur.execute('''
    SELECT supplier_id, shipment_number, expected_delivery, delivered_at,
           (delivered_at::date - expected_delivery) as delay_days
    FROM "Shipments"
    WHERE expected_delivery IS NOT NULL AND delivered_at IS NOT NULL;
''')
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
