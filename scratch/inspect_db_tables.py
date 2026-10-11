import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def inspect():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
        ORDER BY table_name
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Total public tables: {len(tables)}")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM public."{t}"')
        cnt = cur.fetchone()[0]
        print(f"  - {t}: {cnt} rows")
    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect()
