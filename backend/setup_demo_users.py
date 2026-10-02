import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import get_db_connection
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get roles
    cursor.execute('SELECT role_id, role_name FROM public."Roles"')
    roles = {row[1]: row[0] for row in cursor.fetchall()}
    
    password = "password123"
    password_hash = generate_password_hash(password)
    
    users_to_create = [
        ("demo_owner", "owner@demo.com", roles.get("Owner")),
        ("demo_manager", "manager@demo.com", roles.get("Manager")),
        ("demo_employee", "employee@demo.com", roles.get("Employee")),
        ("demo_supplier", "supplier@demo.com", roles.get("Supplier"))
    ]
    
    for username, email, role_id in users_to_create:
        if not role_id: continue
        
        cursor.execute('SELECT user_id FROM public."Users" WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        if user:
            # Update password
            cursor.execute('UPDATE public."Users" SET password_hash = %s WHERE username = %s', (password_hash, username))
        else:
            # Create
            cursor.execute(
                'INSERT INTO public."Users" (username, email, password_hash, role_id, status) VALUES (%s, %s, %s, %s, %s)',
                (username, email, password_hash, role_id, "Active")
            )
            
    conn.commit()
    print("Demo users created/updated successfully!")
    cursor.close()
    conn.close()
