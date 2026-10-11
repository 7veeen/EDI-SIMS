import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT action, table_name, count(*) FROM "AuditLogs" GROUP BY action, table_name ORDER BY count(*) DESC;')
print("Action & Table Breakdown:")
for r in cur.fetchall():
    print(f"  - Action: {r[0]}, Table: {r[1]}, Count: {r[2]}")

cur.execute('SELECT log_id, action, table_name, record_id, user_id, action_time FROM "AuditLogs" ORDER BY log_id ASC;')
print("\nAll 32 logs:")
for r in cur.fetchall():
    print(f"  #{r[0]}: {r[1]} on {r[2]} (id={r[3]}, user={r[4]}) at {r[5]}")

conn.close()
