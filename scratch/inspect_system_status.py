import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def inspect():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT module_name, status, progress, message, updated_at FROM public."SystemStatus" ORDER BY module_name ASC')
    rows = cur.fetchall()
    print("SystemStatus rows count:", len(rows))
    for r in rows:
        print(f" - {r[0]}: status={r[1]}, progress={r[2]}%, msg='{r[3]}', updated={r[4]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect()
