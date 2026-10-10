"""
preflight_inspection.py
Read-only inspection of Reports, StockTransactions, PurchaseOrders, Suppliers, Products, etc.
"""
import os
import sys
import json

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def inspect():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 1. Reports count and reconciliation
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN report_data IS NOT NULL THEN 1 END) as with_snapshot,
                    COUNT(CASE WHEN report_data IS NULL THEN 1 END) as legacy
                FROM "Reports";
            """)
            rep_stats = cur.fetchone()
            print("=== 1. REPORTS TABLE RECONCILIATION ===")
            print(f"Total reports: {rep_stats[0]}")
            print(f"With snapshot: {rep_stats[1]}")
            print(f"Legacy without snapshot: {rep_stats[2]}")

            # Fetch recent reports to see what types exist and identify test records
            cur.execute("""
                SELECT report_id, report_name, report_type, generated_by, generated_on, (report_data IS NOT NULL) as has_snap
                FROM "Reports"
                ORDER BY report_id DESC
                LIMIT 15;
            """)
            recent = cur.fetchall()
            print("\nRecent 15 reports:")
            for r in recent:
                print(f"  ID={r[0]}, Name='{r[1]}', Type='{r[2]}', By={r[3]}, Date={r[4]}, HasSnap={r[5]}")

            # 2. Check existing tables in public schema
            print("\n=== 2. TABLES IN PUBLIC SCHEMA ===")
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [t[0] for t in cur.fetchall()]
            print("Tables found:", tables)

            # 3. Inspect columns for relevant tables
            relevant_tables = [
                'Reports', 
                'StockTransactions', 'stock_transactions', 'Transactions', 'transactions',
                'Products', 'products',
                'Inventory', 'inventory',
                'PurchaseOrders', 'purchase_orders',
                'PurchaseOrderItems', 'purchase_order_items', 'POItems',
                'Suppliers', 'suppliers',
                'Shipments', 'shipments',
                'Users', 'users'
            ]
            
            actual_relevant = [t for t in tables if t in relevant_tables]
            print("\nActual relevant tables matched:", actual_relevant)

            for tbl in actual_relevant:
                print(f"\n--- Columns in \"{tbl}\" ---")
                cur.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = '{tbl}'
                    ORDER BY ordinal_position;
                """)
                for col in cur.fetchall():
                    print(f"  {col[0]}: {col[1]} (Nullable: {col[2]}, Default: {col[3]})")

            # 4. Check sample data and relationships in StockTransactions (or equivalent)
            stock_tbl = next((t for t in ['StockTransactions', 'stock_transactions'] if t in tables), None)
            if stock_tbl:
                print(f"\n=== 4. SAMPLE DATA IN \"{stock_tbl}\" ===")
                cur.execute(f'SELECT COUNT(*) FROM "{stock_tbl}";')
                count = cur.fetchone()[0]
                print(f"Total rows in {stock_tbl}: {count}")
                cur.execute(f'SELECT * FROM "{stock_tbl}" ORDER BY 1 DESC LIMIT 3;')
                sample_rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                print(f"Columns: {col_names}")
                for row in sample_rows:
                    print("Row:", dict(zip(col_names, [str(v) for v in row])))

            # 5. Check sample data and relationships in PurchaseOrders & POItems
            po_tbl = next((t for t in ['PurchaseOrders', 'purchase_orders'] if t in tables), None)
            poi_tbl = next((t for t in ['PurchaseOrderItems', 'purchase_order_items', 'POItems'] if t in tables), None)
            if po_tbl:
                print(f"\n=== 5. SAMPLE DATA IN \"{po_tbl}\" ===")
                cur.execute(f'SELECT COUNT(*) FROM "{po_tbl}";')
                count = cur.fetchone()[0]
                print(f"Total rows in {po_tbl}: {count}")
                cur.execute(f'SELECT * FROM "{po_tbl}" ORDER BY 1 DESC LIMIT 3;')
                sample_rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                print(f"Columns: {col_names}")
                for row in sample_rows:
                    print("Row:", dict(zip(col_names, [str(v) for v in row])))

            if poi_tbl:
                print(f"\n=== SAMPLE DATA IN \"{poi_tbl}\" ===")
                cur.execute(f'SELECT COUNT(*) FROM "{poi_tbl}";')
                count = cur.fetchone()[0]
                print(f"Total rows in {poi_tbl}: {count}")
                cur.execute(f'SELECT * FROM "{poi_tbl}" ORDER BY 1 DESC LIMIT 5;')
                sample_rows = cur.fetchall()
                col_names = [desc[0] for desc in cur.description]
                print(f"Columns: {col_names}")
                for row in sample_rows:
                    print("Row:", dict(zip(col_names, [str(v) for v in row])))

            # 6. Foreign key constraints among these tables
            print("\n=== 6. FOREIGN KEY CONSTRAINTS ===")
            cur.execute("""
                SELECT
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name 
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                  AND tc.table_schema='public'
                  AND (tc.table_name IN ('StockTransactions', 'PurchaseOrders', 'PurchaseOrderItems', 'Reports')
                       OR ccu.table_name IN ('StockTransactions', 'PurchaseOrders', 'PurchaseOrderItems', 'Reports'));
            """)
            for fk in cur.fetchall():
                print(f"  {fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")

if __name__ == "__main__":
    inspect()
