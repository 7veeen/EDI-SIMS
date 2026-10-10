import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM "Reports";')
total_reports = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM "Reports" WHERE report_data IS NOT NULL;')
snapshot_reports = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM "Reports" WHERE report_data IS NULL;')
legacy_reports = cur.fetchone()[0]

cur.execute('''
    SELECT report_type, COUNT(*), 
           COUNT(CASE WHEN report_data IS NOT NULL THEN 1 END) as with_snapshot,
           COUNT(CASE WHEN report_data IS NULL THEN 1 END) as legacy
    FROM "Reports"
    GROUP BY report_type
    ORDER BY report_type;
''')
type_breakdown = cur.fetchall()

print(f"TOTAL REPORTS: {total_reports}")
print(f"SNAPSHOT REPORTS: {snapshot_reports}")
print(f"LEGACY REPORTS: {legacy_reports}")
print("\nType breakdown:")
for r in type_breakdown:
    print(f"  {r[0]:<25}: Total {r[1]:<3} | Snapshots {r[2]:<3} | Legacy {r[3]:<3}")

cur.close()
conn.close()
