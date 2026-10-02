from psycopg2 import Error
from werkzeug.security import generate_password_hash

from app.extensions import get_db_connection


def create_user(username, email, password, role_name, creator_role):
    conn = None
    cursor = None

    try:
        # Check whether the creator is allowed to create the requested role
        allowed_roles = {
            "Owner": ["Owner", "Manager", "Employee", "Supplier"],
            "Manager": ["Employee", "Supplier"]
        }

        if creator_role not in allowed_roles:
            return None, "You do not have permission to create users"

        if role_name not in allowed_roles[creator_role]:
            return None, f"{creator_role} cannot create a {role_name} account"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check whether username already exists
        cursor.execute(
            '''
            SELECT user_id
            FROM public."Users"
            WHERE username = %s
            ''',
            (username,)
        )

        if cursor.fetchone():
            return None, "Username already exists"

        # Check whether email already exists
        cursor.execute(
            '''
            SELECT user_id
            FROM public."Users"
            WHERE email = %s
            ''',
            (email,)
        )

        if cursor.fetchone():
            return None, "Email already exists"

        # Find the requested role
        cursor.execute(
            '''
            SELECT role_id
            FROM public."Roles"
            WHERE role_name = %s
            ''',
            (role_name,)
        )

        role = cursor.fetchone()

        if role is None:
            return None, "Invalid role"

        role_id = role[0]

        # Hash the initial password before storing it
        password_hash = generate_password_hash(password)

        # Create the user
        cursor.execute(
            '''
            INSERT INTO public."Users"
            (username, email, password_hash, role_id, status)
            VALUES (%s, %s, %s, %s, 'Active')
            RETURNING user_id, username, email, role_id, status
            ''',
            (username, email, password_hash, role_id)
        )

        new_user = cursor.fetchone()

        conn.commit()

        return {
            "user_id": new_user[0],
            "username": new_user[1],
            "email": new_user[2],
            "role_id": new_user[3],
            "status": new_user[4]
        }, None

    except Error:
        if conn:
            conn.rollback()

        return None, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def get_users(role_name=None, search=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = '''
            SELECT
                u.user_id,
                u.username,
                u.email,
                r.role_name,
                u.status
            FROM public."Users" u
            JOIN public."Roles" r
                ON u.role_id = r.role_id
        '''

        conditions = []
        parameters = []

        if role_name:
            conditions.append("r.role_name = %s")
            parameters.append(role_name)

        if search:
            conditions.append("u.username ILIKE %s")
            parameters.append(f"%{search}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY u.user_id"

        cursor.execute(query, tuple(parameters))

        rows = cursor.fetchall()

        users = []

        for row in rows:
            users.append({
                "user_id": row[0],
                "username": row[1],
                "email": row[2],
                "role": row[3],
                "status": row[4]
            })

        return users, None

    except Error:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def get_user_by_id(user_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT
                u.user_id,
                u.username,
                u.email,
                r.role_name,
                u.status
            FROM public."Users" u
            JOIN public."Roles" r
                ON u.role_id = r.role_id
            WHERE u.user_id = %s
            ''',
            (user_id,)
        )

        row = cursor.fetchone()

        if row is None:
            return None, "User not found"

        user = {
            "user_id": row[0],
            "username": row[1],
            "email": row[2],
            "role": row[3],
            "status": row[4]
        }

        return user, None

    except Error:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def update_user_status(user_id, status):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE public."Users"
            SET status = %s
            WHERE user_id = %s
            RETURNING user_id, username, email, role_id, status
            ''',
            (status, user_id)
        )

        updated_user = cursor.fetchone()

        if updated_user is None:
            return None, "User not found"

        conn.commit()

        return {
            "user_id": updated_user[0],
            "username": updated_user[1],
            "email": updated_user[2],
            "role_id": updated_user[3],
            "status": updated_user[4]
        }, None

    except Error:
        if conn:
            conn.rollback()

        return None, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def update_username(user_id, new_username):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute(
            '''
            SELECT user_id
            FROM public."Users"
            WHERE username = %s AND user_id != %s
            ''',
            (new_username, user_id)
        )

        if cursor.fetchone():
            return None, "Username already taken"

        cursor.execute(
            '''
            UPDATE public."Users"
            SET username = %s
            WHERE user_id = %s
            RETURNING user_id, username, email, role_id, status
            ''',
            (new_username, user_id)
        )

        updated_user = cursor.fetchone()

        if updated_user is None:
            return None, "User not found"

        conn.commit()

        return {
            "user_id": updated_user[0],
            "username": updated_user[1],
            "email": updated_user[2],
            "role_id": updated_user[3],
            "status": updated_user[4]
        }, None

    except Error:
        if conn:
            conn.rollback()
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()