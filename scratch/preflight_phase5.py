import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

def main():
    conn = get_db_connection()
    cur = conn.cursor()

    print("=== 1. QUOTATION NUMBER GROUPING ===")
    cur.execute("""
        SELECT quotation_number, COUNT(*) 
        FROM "SupplierQuotations" 
        WHERE quotation_number IS NOT NULL 
        GROUP BY quotation_number 
        HAVING COUNT(*) > 1;
    """)
    dups = cur.fetchall()
    print("Duplicate quotation_numbers:", dups)

    cur.execute('SELECT COUNT(*) FROM "SupplierQuotations" WHERE quotation_number IS NULL;')
    print("Quotations with NULL quotation_number:", cur.fetchone()[0])

    cur.execute('SELECT COUNT(*) FROM "SupplierQuotations" WHERE quotation_number IS NOT NULL;')
    print("Quotations with NOT NULL quotation_number:", cur.fetchone()[0])

    print("\n=== 2. SUPPLIERS OVERVIEW ===")
    cur.execute("""
        SELECT supplier_id, supplier_name, contact_person, email, phone, status 
        FROM "Suppliers" 
        ORDER BY supplier_id;
    """)
    suppliers = cur.fetchall()
    for s in suppliers:
        print("Supplier:", s)

    print("\n=== 3. PURCHASE ORDERS BY SUPPLIER ===")
    cur.execute("""
        SELECT s.supplier_id, s.supplier_name, 
               COUNT(po.purchase_order_id) as total_pos,
               COUNT(CASE WHEN po.status = 'Accepted' THEN 1 END) as accepted_pos,
               COUNT(CASE WHEN po.status = 'Rejected' THEN 1 END) as rejected_pos,
               COUNT(CASE WHEN po.status = 'Created' THEN 1 END) as created_pos,
               COALESCE(SUM(po.total_amount), 0) as total_po_value
        FROM "Suppliers" s
        LEFT JOIN "PurchaseOrders" po ON s.supplier_id = po.supplier_id
        GROUP BY s.supplier_id, s.supplier_name
        ORDER BY s.supplier_id;
    """)
    for row in cur.fetchall():
        print(f"PO metrics: Supplier {row[0]} ({row[1]}): Total POs={row[2]}, Accepted={row[3]}, Rejected={row[4]}, Created={row[5]}, TotalVal={row[6]}")

    print("\n=== 4. QUOTATIONS BY SUPPLIER ===")
    cur.execute("""
        SELECT s.supplier_id, s.supplier_name,
               COUNT(q.quotation_id) as total_quotations,
               COUNT(CASE WHEN q.status IN ('Approved', 'Accepted') THEN 1 END) as approved_quotations,
               COUNT(CASE WHEN q.status IN ('Rejected', 'Expired') THEN 1 END) as rejected_quotations,
               COUNT(CASE WHEN q.status IN ('Pending', 'Submitted', 'Under Review', 'Draft') THEN 1 END) as pending_quotations,
               COUNT(CASE WHEN q.status IN ('Submitted', 'Under Review', 'Approved', 'Accepted', 'Rejected') THEN 1 END) as responded_quotations
        FROM "Suppliers" s
        LEFT JOIN "SupplierQuotations" q ON s.supplier_id = q.supplier_id
        GROUP BY s.supplier_id, s.supplier_name
        ORDER BY s.supplier_id;
    """)
    for row in cur.fetchall():
        print(f"Quotation metrics: Supplier {row[0]} ({row[1]}): Total Quots={row[2]}, Approved={row[3]}, Rejected={row[4]}, Pending={row[5]}, Responded={row[6]}")

    print("\n=== 5. SHIPMENTS & DELIVERY PERFORMANCE ===")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'Shipments'
        ORDER BY ordinal_position;
    """)
    for col in cur.fetchall():
        print(f"  Shipment col: {col[0]:<25} {col[1]}")

    cur.execute("""
        SELECT status, COUNT(*),
               COUNT(CASE WHEN expected_delivery IS NOT NULL THEN 1 END) as with_expected_delivery,
               COUNT(CASE WHEN delivered_at IS NOT NULL THEN 1 END) as with_delivered_at,
               COUNT(CASE WHEN shipped_at IS NOT NULL THEN 1 END) as with_shipped_at
        FROM "Shipments"
        GROUP BY status;
    """)
    print("\nShipments status breakdown:")
    for row in cur.fetchall():
        print(f"  Status: {row[0]:<25} Count: {row[1]:<4} ExpectedDeliv: {row[2]:<4} DeliveredAt: {row[3]:<4} ShippedAt: {row[4]:<4}")

    cur.execute("""
        SELECT s.supplier_id, s.supplier_name,
               COUNT(sh.shipment_id) as total_shipments,
               COUNT(CASE WHEN sh.status = 'Delivered' THEN 1 END) as delivered_shipments,
               COUNT(CASE WHEN sh.status != 'Delivered' THEN 1 END) as pending_shipments,
               COUNT(CASE WHEN sh.status = 'Delivered' AND sh.delivered_at IS NOT NULL AND sh.expected_delivery IS NOT NULL AND sh.delivered_at::date <= sh.expected_delivery THEN 1 END) as on_time_shipments,
               COUNT(CASE WHEN sh.status = 'Delivered' AND sh.delivered_at IS NOT NULL AND sh.expected_delivery IS NOT NULL AND sh.delivered_at::date > sh.expected_delivery THEN 1 END) as late_shipments
        FROM "Suppliers" s
        LEFT JOIN "Shipments" sh ON s.supplier_id = sh.supplier_id
        GROUP BY s.supplier_id, s.supplier_name
        ORDER BY s.supplier_id;
    """)
    print("\nShipments by supplier:")
    for row in cur.fetchall():
        print(f"  Supplier {row[0]} ({row[1]}): Total Shipments={row[2]}, Delivered={row[3]}, Pending={row[4]}, On-Time={row[5]}, Late={row[6]}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
