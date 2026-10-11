import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute('SELECT u.user_id, u.username, r.role_name, u.status FROM public."Users" u JOIN public."Roles" r ON u.role_id = r.role_id ORDER BY u.user_id ASC;')
for r in cur.fetchall():
    print(r)
conn.close()
