import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

# 1. Triggers
cur.execute('''
    SELECT event_object_table, trigger_name, action_timing, event_manipulation 
    FROM information_schema.triggers 
    WHERE trigger_schema = 'public';
''')
triggers = cur.fetchall()
print(f"Total triggers: {len(triggers)}")
for t in triggers:
    print("  Trigger:", t)

# 2. AuditLogs constraints
cur.execute('''
    SELECT conname, contype, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'public' AND conrelid = 'public."AuditLogs"'::regclass;
''')
constraints = cur.fetchall()
print(f"\nAuditLogs Constraints ({len(constraints)}):")
for c in constraints:
    print(f"  {c[0]} ({c[1]}): {c[2]}")

# 3. Foreign key from user_id in AuditLogs?
cur.execute('''
    SELECT column_name, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'AuditLogs'
    ORDER BY ordinal_position;
''')
cols = cur.fetchall()
print(f"\nAuditLogs Columns ({len(cols)}):")
for col in cols:
    print(f"  {col[0]}: nullable={col[1]}, default={col[2]}")

conn.close()
