import psycopg2
from app.config import DATABASE_URL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
cursor.execute('SELECT * FROM public."Inventory" LIMIT 1')
print([desc[0] for desc in cursor.description])
