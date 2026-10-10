import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

def inspect_phase6():
    conn = get_db_connection()
    cur = conn.cursor()

    print("=== 1. AUDITLOGS SCHEMA INSPECTION ===")
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'AuditLogs'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    print("Columns for AuditLogs:")
    for c in cols:
        print(f"  {c[0]:<25} {c[1]:<20} Nullable: {c[2]:<4} Default: {c[3]}")

    cur.execute("""
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
          ON ccu.constraint_name = tc.constraint_name
          AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'AuditLogs';
    """)
    fks = cur.fetchall()
    print("\nForeign keys for AuditLogs:")
    for fk in fks:
        print(f"  {fk[0]} -> {fk[1]}({fk[2]})")

    cur.execute('SELECT COUNT(*) FROM "AuditLogs";')
    audit_count = cur.fetchone()[0]
    print(f"\nTotal row count in AuditLogs: {audit_count}")

    cur.execute('SELECT DISTINCT action FROM "AuditLogs";')
    actions = [r[0] for r in cur.fetchall()]
    print(f"Distinct actions in AuditLogs: {actions}")

    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = 'AuditLogs' AND column_name IN ('entity', 'table_name', 'entity_type', 'target_table', 'module');
    """)
    entity_col = cur.fetchall()
    print(f"Entity-like columns: {entity_col}")

    cur.execute('SELECT * FROM "AuditLogs" ORDER BY 1 DESC LIMIT 5;')
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print("\nRecent AuditLogs samples:")
    for r in rows:
        print("  Row:", dict(zip(col_names, r)))

    print("\n=== 2. REPORTS RECONCILIATION ===")
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

    print(f"Total reports: {total_reports}")
    print(f"Snapshots (report_data IS NOT NULL): {snapshot_reports}")
    print(f"Legacy reports (report_data IS NULL): {legacy_reports}")
    print("\nBreakdown by report_type:")
    for r in type_breakdown:
        print(f"  {r[0]:<25}: Total {r[1]:<3} | Snapshots {r[2]:<3} | Legacy {r[3]:<3}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    inspect_phase6()
