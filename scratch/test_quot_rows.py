import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute("""
    SELECT q.quotation_id, q.quotation_number, q.purchase_order_id, q.supplier_id, s.supplier_name,
           q.product_id, p.product_name, q.quantity, q.quoted_price, q.total_amount, q.status, q.notes
    FROM "SupplierQuotations" q
    JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
    JOIN "Products" p ON q.product_id = p.product_id
    WHERE q.quotation_number IN ('QT-2026-0016', 'QT-2026-0012')
    ORDER BY q.quotation_number, q.quotation_id;
""")
for r in cur.fetchall():
    print("Multi-item quotation row:", r)

print("\n--- Samples with NULL quotation_number ---")
cur.execute("""
    SELECT q.quotation_id, q.quotation_number, q.purchase_order_id, q.supplier_id, s.supplier_name,
           q.product_id, p.product_name, q.quantity, q.quoted_price, q.total_amount, q.status, q.notes
    FROM "SupplierQuotations" q
    JOIN "Suppliers" s ON q.supplier_id = s.supplier_id
    JOIN "Products" p ON q.product_id = p.product_id
    WHERE q.quotation_number IS NULL
    LIMIT 3;
""")
for r in cur.fetchall():
    print("Null quotation_number row:", r)

cur.close()
conn.close()
