import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def inspect():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT backup_id, backup_name, backup_type, backup_date, backup_size, created_by, status FROM "BackupHistory" ORDER BY backup_id DESC')
    rows = cur.fetchall()
    print(f"Total BackupHistory records: {len(rows)}")
    for r in rows:
        print(" ", r)
    cur.close()
    conn.close()

if __name__ == "__main__":
    inspect()
