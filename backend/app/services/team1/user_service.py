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

def get_users(creator_role=None, role_name=None, search=None, page=None, page_size=None, sort_by=None, sort_order=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        conditions = []
        parameters = []

        # Role scoping based on creator_role
        if creator_role == "Manager":
            if role_name:
                if role_name not in ["Employee", "Supplier"]:
                    return None, 0, "You do not have permission to view users with this role"
                conditions.append("r.role_name = %s")
                parameters.append(role_name)
            else:
                conditions.append("r.role_name IN ('Employee', 'Supplier')")
        else:
            if role_name:
                conditions.append("r.role_name = %s")
                parameters.append(role_name)

        if search:
            conditions.append("(u.username ILIKE %s OR u.email ILIKE %s)")
            parameters.extend([f"%{search}%", f"%{search}%"])

        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)

        # Get total count
        count_query = '''
            SELECT count(*)
            FROM public."Users" u
            JOIN public."Roles" r
                ON u.role_id = r.role_id
        ''' + where_clause

        cursor.execute(count_query, tuple(parameters))
        total_count = cursor.fetchone()[0]

        # Sorting whitelist
        sort_map = {
            "user_id": "u.user_id",
            "username": "u.username",
            "email": "u.email",
            "role": "r.role_name",
            "status": "u.status"
        }
        order_col = sort_map.get((sort_by or "").lower(), "u.user_id")
        order_dir = "DESC" if str(sort_order).upper() == "DESC" else "ASC"
        order_clause = f" ORDER BY {order_col} {order_dir}"

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
        ''' + where_clause + order_clause

        query_params = list(parameters)

        if page is not None:
            try:
                page_num = max(1, int(page))
            except (ValueError, TypeError):
                page_num = 1
            try:
                limit_num = max(1, min(100, int(page_size or 10)))
            except (ValueError, TypeError):
                limit_num = 10

            offset_num = (page_num - 1) * limit_num
            query += " LIMIT %s OFFSET %s"
            query_params.extend([limit_num, offset_num])

        cursor.execute(query, tuple(query_params))

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

        return users, total_count, None

    except Error:
        return None, 0, "Database error"

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