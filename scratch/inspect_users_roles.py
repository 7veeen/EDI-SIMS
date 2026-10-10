import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
c = conn.cursor()

c.execute('SELECT user_id, username, status, role_id FROM "Users" LIMIT 5')
print("USERS:", c.fetchall(), flush=True)

c.execute('SELECT role_id, role_name FROM "Roles"')
print("ROLES:", c.fetchall(), flush=True)

c.execute('SELECT supplier_id, user_id, supplier_name, status FROM "Suppliers" LIMIT 5')
print("SUPPLIERS:", c.fetchall(), flush=True)

conn.close()
