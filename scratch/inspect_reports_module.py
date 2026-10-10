import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from app.extensions import get_db_connection

def main():
    conn = get_db_connection()
    c = conn.cursor()

    print("--- 1. REPORTS TABLE SCHEMA ---")
    c.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'Reports'
        ORDER BY ordinal_position
    """)
    for col in c.fetchall():
        print(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

    print("\n--- 2. SYSTEMSTATUS TABLE SCHEMA ---")
    c.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'SystemStatus'
        ORDER BY ordinal_position
    """)
    for col in c.fetchall():
        print(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

    print("\n--- 3. SYSTEMSTATUS ROWS ---")
    c.execute('SELECT * FROM "SystemStatus"')
    for row in c.fetchall():
        print(f"  {row}")

    print("\n--- 4. REPORTS COUNT & SAMPLE ROWS ---")
    c.execute('SELECT COUNT(*) FROM "Reports"')
    print(f"  Total Reports count: {c.fetchone()[0]}")

    c.execute('SELECT report_id, report_name, report_type, generated_by, generated_on FROM "Reports" ORDER BY report_id DESC LIMIT 5')
    for row in c.fetchall():
        print(f"  Report #{row[0]}: name='{row[1]}', type='{row[2]}', by=User#{row[3]}, on={row[4]}")

    print("\n--- 5. CHECK IF THERE ARE OTHER REPORT TABLES / VIEWS ---")
    c.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name ILIKE '%report%'
    """)
    for row in c.fetchall():
        print(f"  {row[0]} ({row[1]})")

    conn.close()

if __name__ == '__main__':
    main()
