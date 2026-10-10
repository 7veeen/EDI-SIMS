import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
c = conn.cursor()

c.execute("""
    SELECT trigger_name, event_manipulation, event_object_table 
    FROM information_schema.triggers 
    WHERE event_object_schema = 'public'
""")
print('TRIGGERS:', c.fetchall(), flush=True)

c.execute("""
    SELECT routine_name 
    FROM information_schema.routines 
    WHERE routine_schema = 'public' AND routine_type = 'FUNCTION'
""")
print('FUNCTIONS:', [r[0] for r in c.fetchall()], flush=True)

conn.close()
