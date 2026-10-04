import os, psycopg2
from dotenv import load_dotenv

load_dotenv('backend/.env')
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

cur.execute('''
    SELECT u.user_id, u.username, u.email, r.role_name 
    FROM "Users" u
    JOIN "Roles" r ON u.role_id = r.role_id
    WHERE r.role_name = 'Supplier'
''')
print('Supplier Users:')
for u in cur.fetchall():
    print(' ', u)

cur.execute('SELECT supplier_id, user_id, supplier_name, email, phone FROM "Suppliers"')
print('\nSuppliers:')
for s in cur.fetchall():
    print(' ', s)

cur.execute('SELECT stock_request_id, request_number, supplier_id, status FROM "StockRequests"')
print('\nStock Requests:')
for r in cur.fetchall():
    print(' ', r)

cur.close()
conn.close()
