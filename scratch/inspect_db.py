import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv("d:/7even repica 2/.env")
db_url = os.getenv("DATABASE_URL")
print(f"Testing DB URL: {db_url[:40]}...")

try:
    conn = psycopg2.connect(db_url, connect_timeout=10)
    # Enforce read-only transaction on session level
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print("Database connection successful!")

    # 1. Check if public."ShipmentItems" exists
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'ShipmentItems';
    """)
    res = cur.fetchall()
    print("Table lookup for 'ShipmentItems':", res)

    # 2. Check all tables in public schema
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = [r['table_name'] for r in cur.fetchall()]
    print("All public tables:", tables)

    # 3. Check migration tables in all schemas
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables 
        WHERE table_name ILIKE '%migration%' OR table_name ILIKE '%schema%' OR table_name ILIKE '%version%'
        ORDER BY table_schema, table_name;
    """)
    mig_tables = cur.fetchall()
    print("Migration/version tables in DB:", mig_tables)

    # 4. If supabase_migrations exists in supabase_migrations schema or similar
    cur.execute("""
        SELECT schema_name FROM information_schema.schemata;
    """)
    schemas = [r['schema_name'] for r in cur.fetchall()]
    print("Schemas in DB:", schemas)

    # If ShipmentItems exists, inspect its columns
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'ShipmentItems'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    print("\nColumns of 'ShipmentItems':")
    for c in cols:
        print("  ", dict(c))

    # Inspect constraints on ShipmentItems
    cur.execute("""
        SELECT
            con.conname AS constraint_name,
            con.contype AS constraint_type,
            pg_get_constraintdef(con.oid) AS constraint_definition
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE nsp.nspname = 'public' AND rel.relname = 'ShipmentItems';
    """)
    constraints = cur.fetchall()
    print("\nConstraints on 'ShipmentItems':")
    for c in constraints:
        print("  ", dict(c))

    # Inspect indexes on ShipmentItems
    cur.execute("""
        SELECT
            i.relname AS index_name,
            pg_get_indexdef(idx.indexrelid) AS index_definition
        FROM pg_index idx
        JOIN pg_class i ON i.oid = idx.indexrelid
        JOIN pg_class c ON c.oid = idx.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relname = 'ShipmentItems';
    """)
    indexes = cur.fetchall()
    print("\nIndexes on 'ShipmentItems':")
    for idx in indexes:
        print("  ", dict(idx))

    # Count rows in ShipmentItems
    cur.execute('SELECT COUNT(*) AS total_count FROM public."ShipmentItems";')
    cnt = cur.fetchone()
    print("\nTotal rows in ShipmentItems:", cnt)

    # Count rows in Shipments
    cur.execute('SELECT COUNT(*) AS total_shipments FROM public."Shipments";')
    shipments_cnt = cur.fetchone()
    print("Total shipments in Shipments:", shipments_cnt)

    # Count shipments with and without allocation records
    cur.execute('''
        SELECT 
            COUNT(s.shipment_id) AS total_shipments,
            COUNT(DISTINCT si.shipment_id) AS shipments_with_allocations,
            COUNT(s.shipment_id) - COUNT(DISTINCT si.shipment_id) AS shipments_without_allocations
        FROM public."Shipments" s
        LEFT JOIN public."ShipmentItems" si ON s.shipment_id = si.shipment_id;
    ''')
    alloc_summary = cur.fetchone()
    print("Shipment allocation summary:", alloc_summary)

    # If any rows exist in ShipmentItems, inspect a few
    cur.execute('SELECT * FROM public."ShipmentItems" LIMIT 10;')
    sample_allocs = cur.fetchall()
    print("Sample ShipmentItems rows:", sample_allocs)

    # Check foreign key consistency (orphans)
    cur.execute('''
        SELECT COUNT(*) AS orphan_shipments
        FROM public."ShipmentItems" si
        LEFT JOIN public."Shipments" s ON si.shipment_id = s.shipment_id
        WHERE s.shipment_id IS NULL;
    ''')
    orphan_shipments = cur.fetchone()
    print("Orphan shipment_ids in ShipmentItems:", orphan_shipments)

    cur.execute('''
        SELECT COUNT(*) AS orphan_products
        FROM public."ShipmentItems" si
        LEFT JOIN public."Products" p ON si.product_id = p.product_id
        WHERE p.product_id IS NULL;
    ''')
    orphan_products = cur.fetchone()
    print("Orphan product_ids in ShipmentItems:", orphan_products)

    # Check migration history tables if any exist
    for mig_schema in ['supabase_migrations', 'public', '_supabase']:
        if mig_schema in schemas:
            cur.execute(f"""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = '{mig_schema}';
            """)
            tbls = [r['table_name'] for r in cur.fetchall()]
            print(f"Tables in {mig_schema}:", tbls)
            for t in tbls:
                if 'migration' in t.lower() or 'schema' in t.lower():
                    cur.execute(f'SELECT * FROM "{mig_schema}"."{t}" ORDER BY 1;')
                    print(f"Content of {mig_schema}.{t}:", cur.fetchall())

    cur.close()
    conn.close()

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
