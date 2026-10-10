import os
import sys

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.team3.report_service import get_db_connection

def reconcile():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM "Reports"')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "Reports" WHERE report_data IS NOT NULL')
    snaps = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM "Reports" WHERE report_data IS NULL')
    leg = cur.fetchone()[0]
    cur.execute('SELECT report_type, COUNT(*) FROM "Reports" GROUP BY report_type ORDER BY COUNT(*) DESC')
    types = cur.fetchall()
    cur.execute('SELECT COUNT(*) FROM "AuditLogs"')
    audits = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"TOTAL_REPORTS: {total}")
    print(f"SNAPSHOT_REPORTS: {snaps}")
    print(f"LEGACY_REPORTS: {leg}")
    print(f"AUDIT_LOGS_COUNT: {audits}")
    print("COUNTS BY TYPE:")
    for t, c in types:
        print(f"  - {t}: {c}")

if __name__ == "__main__":
    reconcile()
