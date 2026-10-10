import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'SupplierQuotations'
    ORDER BY ordinal_position;
""")
cols = cur.fetchall()
print("COLUMNS FOR SupplierQuotations:")
for col in cols:
    print(f"  {col[0]:<25} {col[1]:<20} Nullable: {col[2]:<4} Default: {col[3]}")

cur.execute("""
    SELECT
        kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'SupplierQuotations';
""")
fks = cur.fetchall()
print("\nForeign keys:")
for fk in fks:
    print(f"  {fk[0]} -> {fk[1]}({fk[2]})")

cur.execute('SELECT COUNT(*) FROM "SupplierQuotations";')
print("\nTotal Row count in SupplierQuotations:", cur.fetchone()[0])

cur.execute('SELECT DISTINCT status FROM "SupplierQuotations";')
print("Distinct status values in SupplierQuotations:", [r[0] for r in cur.fetchall()])

cur.execute('SELECT * FROM "SupplierQuotations" LIMIT 3;')
rows = cur.fetchall()
col_names = [desc[0] for desc in cur.description]
print("\nColumn names:", col_names)
for r in rows:
    print("Row:", dict(zip(col_names, r)))

# Also check OrderStatusHistory or other related tables if any
cur.execute('SELECT COUNT(*) FROM "OrderStatusHistory";')
print('\nTotal OrderStatusHistory rows:', cur.fetchone()[0])
cur.execute('SELECT * FROM "OrderStatusHistory" LIMIT 3;')
for r in cur.fetchall():
    print('OrderStatusHistory sample:', r)

cur.close()
conn.close()
