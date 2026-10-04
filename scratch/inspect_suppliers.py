import sys
sys.path.insert(0, 'backend')
import psycopg2
from app.config import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT u.user_id, u.username, s.supplier_id, s.supplier_name FROM "Users" u JOIN "Suppliers" s ON u.user_id = s.user_id')
for row in cur.fetchall():
    print(row)
cur.close()
conn.close()
