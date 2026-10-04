import os, psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

tables_to_check = [
    'Suppliers', 'Users', 'Roles', 'Products', 'Categories', 'Inventory',
    'PurchaseOrders', 'PurchaseOrderItems', 'SupplierQuotations', 'Shipments',
    'StockRequests', 'StockRequestItems', 'OrderStatusHistory', 'Payments', 'Invoices', 'StockTransactions'
]

print("=== TABLE EXISTENCE & ROW COUNTS ===")
for t in tables_to_check:
    cur.execute('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        );
    ''', (t,))
    exists = cur.fetchone()[0]
    if exists:
        cur.execute(f'SELECT count(*) FROM "{t}"')
        cnt = cur.fetchone()[0]
        print(f'Table "{t}": EXISTS (row count: {cnt})')
    else:
        print(f'Table "{t}": DOES NOT EXIST')

print("\n=== FOREIGN KEYS & COLUMNS IN KEY TABLES ===")
for t in ['Suppliers', 'PurchaseOrders', 'SupplierQuotations', 'Shipments', 'StockRequests']:
    cur.execute('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = %s
        );
    ''', (t,))
    if cur.fetchone()[0]:
        print(f"\n--- Columns in {t} ---")
        cur.execute('''
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        ''', (t,))
        for col in cur.fetchall():
            print(f"  {col[0]} ({col[1]}, nullable: {col[2]})")

cur.close()
conn.close()
