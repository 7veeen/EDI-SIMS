import sys
sys.path.insert(0, 'backend')
from app.extensions import get_db_connection

conn = get_db_connection()
c = conn.cursor()

c.execute("""
    SELECT notification_type, priority, reference_type, count(*), 
           sum(case when is_read then 1 else 0 end) as read_count,
           sum(case when not is_read then 1 else 0 end) as unread_count
    FROM public."Notifications"
    GROUP BY notification_type, priority, reference_type
    ORDER BY count(*) DESC
""")
print("=== NOTIFICATIONS TABLE BREAKDOWN ===", flush=True)
for row in c.fetchall():
    print(f"Type: {row[0]:<22} | Priority: {row[1]:<8} | Ref: {str(row[2]):<14} | Total: {row[3]:<3} | Read: {row[4]:<3} | Unread: {row[5]:<3}", flush=True)

c.execute("""
    SELECT u.username, r.role_name, count(n.notification_id) as total,
           sum(case when n.is_read then 1 else 0 end) as read_count,
           sum(case when not n.is_read then 1 else 0 end) as unread_count
    FROM public."Users" u
    JOIN public."Roles" r ON u.role_id = r.role_id
    LEFT JOIN public."Notifications" n ON u.user_id = n.user_id
    GROUP BY u.user_id, u.username, r.role_name
    ORDER BY u.user_id
""")
print("\n=== USER NOTIFICATION ISOLATION SUMMARY ===", flush=True)
for row in c.fetchall():
    print(f"User: {row[0]:<15} | Role: {row[1]:<10} | Total: {row[2]:<3} | Read: {row[3]:<3} | Unread: {row[4]:<3}", flush=True)

conn.close()
