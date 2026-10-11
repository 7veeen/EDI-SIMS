import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.extensions import get_db_connection

def check_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM public."AuditLogs"')
    count = cur.fetchone()[0]
    print(f"Total AuditLogs count: {count}")
    
    cur.execute('SELECT log_id, user_id, action, table_name, record_id, action_time, ip_address FROM public."AuditLogs" ORDER BY log_id DESC LIMIT 5')
    rows = cur.fetchall()
    print("Latest 5 records:")
    for r in rows:
        print(" ", r)
        
    cur.execute('SELECT log_id, user_id, action, table_name, record_id, action_time, ip_address FROM public."AuditLogs" ORDER BY log_id ASC LIMIT 5')
    rows_asc = cur.fetchall()
    print("First 5 records:")
    for r in rows_asc:
        print(" ", r)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_db()
