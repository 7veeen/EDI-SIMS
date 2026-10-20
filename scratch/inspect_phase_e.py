import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv("d:/7even repica 2/.env")
db_url = os.getenv("DATABASE_URL")

# Parse sanitized host
parsed = urlparse(db_url)
sanitized_host = f"{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
print(f"Target Database: {sanitized_host}")

try:
    conn = psycopg2.connect(db_url, connect_timeout=10)
    # Strictly read-only session
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print("Database connection successfully established in READ-ONLY mode.")

    # 1. Inspect PurchaseOrders
    cur.execute('SELECT COUNT(*) as total_pos, status, supplier_response FROM "PurchaseOrders" GROUP BY status, supplier_response ORDER BY status;')
    po_summary = cur.fetchall()
    print("\n--- Purchase Orders Status Summary ---")
    for r in po_summary:
        print(" ", dict(r))

    cur.execute("""
        SELECT po.purchase_order_id, po.status, po.supplier_response, s.supplier_name, COUNT(poi.purchase_order_item_id) as item_count
        FROM "PurchaseOrders" po
        JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
        LEFT JOIN "PurchaseOrderItems" poi ON po.purchase_order_id = poi.purchase_order_id
        WHERE po.supplier_response = 'Accepted' OR po.status = 'Accepted'
        GROUP BY po.purchase_order_id, po.status, po.supplier_response, s.supplier_name
        ORDER BY po.purchase_order_id DESC
        LIMIT 10;
    """)
    accepted_pos = cur.fetchall()
    print("\n--- Sample Accepted Purchase Orders (Potential Creation Candidates) ---")
    for r in accepted_pos:
        print(" ", dict(r))

    # 2. Check for explicit test/mock POs or Products
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'PurchaseOrders';
    """)
    po_cols = [r['column_name'] for r in cur.fetchall()]
    print("\nColumns in 'PurchaseOrders':", po_cols)

    # Search for test keywords across text columns
    cur.execute("""
        SELECT purchase_order_id, status, supplier_response
        FROM "PurchaseOrders"
        WHERE rejection_reason ILIKE '%test%' OR rejection_reason ILIKE '%mock%';
    """)
    test_pos = cur.fetchall()
    print(f"\nExplicitly labeled Test POs found ({len(test_pos)}):", test_pos)

    cur.execute("""
        SELECT product_id, product_name, sku, category_id
        FROM "Products"
        WHERE product_name ILIKE '%test%' OR sku ILIKE '%test%' OR product_name ILIKE '%mock%';
    """)
    test_products = cur.fetchall()
    print(f"Explicitly labeled Test Products found ({len(test_products)}):", test_products)

    # 3. Inspect Shipments & ShipmentItems
    cur.execute('SELECT COUNT(*) as total_shipments, status, receiving_status FROM "Shipments" GROUP BY status, receiving_status ORDER BY status;')
    shipment_summary = cur.fetchall()
    print("\n--- Shipments Summary ---")
    for r in shipment_summary:
        print(" ", dict(r))

    cur.execute('SELECT COUNT(*) as count FROM "ShipmentItems";')
    si_count = cur.fetchone()['count']
    print(f"\nTotal rows in 'ShipmentItems': {si_count}")

    # 4. Inspect StockTransactions
    cur.execute('SELECT COUNT(*) as total_txs, transaction_type FROM "StockTransactions" GROUP BY transaction_type;')
    tx_summary = cur.fetchall()
    print("\n--- Stock Transactions Summary ---")
    for r in tx_summary:
        print(" ", dict(r))

    # 5. Inspect Inventory count
    cur.execute('SELECT COUNT(*) as total_inventory_records FROM "Inventory";')
    inv_count = cur.fetchone()['total_inventory_records']
    print(f"\nTotal inventory rows: {inv_count}")

    # 6. Inspect Triggers on Shipments, ShipmentItems, StockTransactions, Inventory, PurchaseOrders
    cur.execute("""
        SELECT 
            event_object_table AS table_name,
            trigger_name,
            event_manipulation AS event,
            action_statement,
            action_timing
        FROM information_schema.triggers
        WHERE event_object_schema = 'public'
          AND event_object_table IN ('Shipments', 'ShipmentItems', 'StockTransactions', 'Inventory', 'PurchaseOrders')
        ORDER BY event_object_table, trigger_name;
    """)
    triggers = cur.fetchall()
    print("\n--- Database Triggers on Core Tables ---")
    if triggers:
        for t in triggers:
            print(" ", dict(t))
    else:
        print("  No custom triggers found on core tables.")

    # 7. Inspect Foreign Keys pointing to Shipments and ShipmentItems
    cur.execute("""
        SELECT
            tc.table_schema, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            rc.delete_rule
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.referential_constraints AS rc
          ON tc.constraint_name = rc.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
          ON rc.unique_constraint_name = ccu.constraint_name
          AND rc.unique_constraint_schema = ccu.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND (ccu.table_name IN ('Shipments', 'ShipmentItems') OR tc.table_name IN ('Shipments', 'ShipmentItems'))
        ORDER BY tc.table_name, kcu.column_name;
    """)
    fks = cur.fetchall()
    print("\n--- Foreign Key Relationships involving Shipments / ShipmentItems ---")
    for f in fks:
        print(" ", dict(f))

    # 8. Check AuditLogs or OrderStatusHistory
    cur.execute('SELECT COUNT(*) as count FROM "OrderStatusHistory";')
    osh_count = cur.fetchone()['count']
    print(f"\nTotal OrderStatusHistory rows: {osh_count}")

    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'AuditLogs'
        ) as exists;
    """)
    al_exists = cur.fetchone()['exists']
    print(f"'AuditLogs' table exists: {al_exists}")
    if al_exists:
        cur.execute('SELECT COUNT(*) as count FROM "AuditLogs";')
        print("Total AuditLogs rows:", cur.fetchone()['count'])

    cur.close()
    conn.close()

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
