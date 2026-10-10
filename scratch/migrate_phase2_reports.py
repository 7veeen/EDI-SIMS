import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection

def main():
    conn = get_db_connection()
    c = conn.cursor()

    print("=== EXECUTING MINIMAL SCHEMA MIGRATION: ADD report_data JSONB TO Reports ===")
    c.execute('SELECT COUNT(*) FROM "Reports"')
    count_before = c.fetchone()[0]
    print(f"Reports row count before migration: {count_before}")

    # Check if column already exists
    c.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'Reports' AND column_name = 'report_data'
    """)
    existing = c.fetchone()
    if existing:
        print(f"Column 'report_data' already exists with type: {existing[1]}")
    else:
        print("Adding column 'report_data JSONB DEFAULT NULL'...")
        c.execute('ALTER TABLE "Reports" ADD COLUMN IF NOT EXISTS report_data JSONB DEFAULT NULL')
        conn.commit()
        print("Column 'report_data' added successfully.")

    # Verify column existence and attributes
    c.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'Reports'
        ORDER BY ordinal_position
    """)
    print("\nUpdated Columns in 'Reports':")
    for col in c.fetchall():
        print(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

    # Verify existing rows are preserved with NULL report_data
    c.execute('SELECT COUNT(*) FROM "Reports"')
    count_after = c.fetchone()[0]
    print(f"\nReports row count after migration: {count_after}")
    assert count_before == count_after, f"Row count changed! {count_before} vs {count_after}"

    c.execute('SELECT COUNT(*) FROM "Reports" WHERE report_data IS NULL')
    null_count = c.fetchone()[0]
    print(f"Legacy reports with report_data IS NULL: {null_count} / {count_after}")

    conn.close()
    print("Migration verified successfully!")

if __name__ == '__main__':
    main()
