import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv("d:/7even repica 2/.env")
db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url, connect_timeout=10)
conn.set_session(readonly=True, autocommit=True)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Let's inspect git history for database/migrations/003_create_shipment_items.sql
# And also check if any table in PostgreSQL tracks migrations applied to public schema.
cur.execute("""
    SELECT schemaname, tablename 
    FROM pg_tables 
    WHERE tablename LIKE '%migration%' OR tablename LIKE '%history%' OR tablename LIKE '%schema%';
""")
print("Matching pg_tables:", cur.fetchall())

# Check pg_stat_user_tables or similar for public.ShipmentItems creation/modification stats if available
cur.execute("""
    SELECT relname, n_live_tup, last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
    FROM pg_stat_user_tables
    WHERE relname IN ('ShipmentItems', 'Shipments', 'SupplierPayments', 'SupplierInvoices');
""")
print("Table stats:", cur.fetchall())

cur.close()
conn.close()
