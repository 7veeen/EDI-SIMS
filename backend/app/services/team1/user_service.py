import re
from psycopg2 import Error
from werkzeug.security import generate_password_hash

from app.extensions import get_db_connection

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


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

def log_user_audit(cursor, actor_id, action, target_user_id, ip_address=None):
    try:
        cursor.execute(
            '''
            INSERT INTO public."AuditLogs" (user_id, action, table_name, record_id, ip_address)
            VALUES (%s, %s, 'Users', %s, %s)
            ''',
            (actor_id, action, target_user_id, ip_address or '127.0.0.1')
        )
    except Exception:
        pass


def count_active_owners(exclude_user_id=None):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if exclude_user_id:
            cursor.execute('''
                SELECT COUNT(*)
                FROM public."Users" u
                JOIN public."Roles" r ON u.role_id = r.role_id
                WHERE r.role_name = 'Owner' AND u.status = 'Active' AND u.user_id != %s
            ''', (exclude_user_id,))
        else:
            cursor.execute('''
                SELECT COUNT(*)
                FROM public."Users" u
                JOIN public."Roles" r ON u.role_id = r.role_id
                WHERE r.role_name = 'Owner' AND u.status = 'Active'
            ''')
        row = cursor.fetchone()
        return (row[0] if row else 0), None
    except Error:
        return 0, "Database error"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_user_status(user_id, status, actor_id=None, ip_address=None):
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
            RETURNING user_id
            ''',
            (status, user_id)
        )

        row = cursor.fetchone()

        if row is None:
            return None, "User not found"

        if actor_id:
            action = "USER_DEACTIVATED" if status == "Inactive" else "USER_REACTIVATED"
            log_user_audit(cursor, actor_id, action, user_id, ip_address)

        conn.commit()

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
        updated = cursor.fetchone()

        return {
            "user_id": updated[0],
            "username": updated[1],
            "email": updated[2],
            "role": updated[3],
            "status": updated[4]
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


def update_user(target_user_id, actor_id, actor_role, username=None, email=None, role_name=None, ip_address=None):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch target user
        cursor.execute(
            '''
            SELECT u.user_id, u.username, u.email, r.role_name, u.status
            FROM public."Users" u
            JOIN public."Roles" r ON u.role_id = r.role_id
            WHERE u.user_id = %s
            ''',
            (target_user_id,)
        )
        target = cursor.fetchone()
        if not target:
            return None, "User not found", 404

        cur_id, cur_username, cur_email, cur_role, cur_status = target

        # 2. RBAC check on target user
        if actor_role == "Manager":
            if cur_role not in ["Employee", "Supplier"]:
                return None, "You do not have permission to edit this user", 403
            if role_name is not None and role_name in ["Owner", "Manager"]:
                return None, "Managers cannot assign Owner or Manager roles", 403
            if role_name is not None and role_name not in ["Employee", "Supplier"]:
                return None, "Invalid role", 400

        # 3. Role modification protection
        new_role_id = None
        role_changed = False
        if role_name is not None:
            # Prevent self-role modification
            if actor_id == target_user_id and role_name != cur_role:
                return None, "You cannot change your own role", 403

            # Verify role exists in Roles table
            cursor.execute(
                '''
                SELECT role_id FROM public."Roles" WHERE role_name = %s
                ''',
                (role_name,)
            )
            role_row = cursor.fetchone()
            if not role_row:
                return None, "Invalid role", 400
            new_role_id = role_row[0]

            if role_name != cur_role:
                role_changed = True
                # If target is active Owner and role is changing away from Owner, verify not last active owner
                if cur_role == "Owner" and cur_status == "Active":
                    cursor.execute(
                        '''
                        SELECT COUNT(*)
                        FROM public."Users" u
                        JOIN public."Roles" r ON u.role_id = r.role_id
                        WHERE r.role_name = 'Owner' AND u.status = 'Active' AND u.user_id != %s
                        ''',
                        (target_user_id,)
                    )
                    active_owners = cursor.fetchone()[0]
                    if active_owners == 0:
                        return None, "Cannot change role of the last active Owner account", 403

        # 4. Username validation
        new_username = cur_username
        if username is not None:
            username_cleaned = username.strip()
            if not username_cleaned:
                return None, "Username cannot be empty", 400
            
            # Check uniqueness if changed
            if username_cleaned != cur_username:
                cursor.execute(
                    '''
                    SELECT user_id FROM public."Users" WHERE username = %s AND user_id != %s
                    ''',
                    (username_cleaned, target_user_id)
                )
                if cursor.fetchone():
                    return None, "Username already exists", 409
                new_username = username_cleaned

        # 5. Email validation
        new_email = cur_email
        if email is not None:
            email_cleaned = email.strip()
            if not email_cleaned:
                return None, "Email cannot be empty", 400
            if not EMAIL_REGEX.match(email_cleaned):
                return None, "Invalid email address format", 400
            
            # Check uniqueness if changed
            if email_cleaned != cur_email:
                cursor.execute(
                    '''
                    SELECT user_id FROM public."Users" WHERE email = %s AND user_id != %s
                    ''',
                    (email_cleaned, target_user_id)
                )
                if cursor.fetchone():
                    return None, "Email already exists", 409
                new_email = email_cleaned

        # 6. Apply updates
        update_fields = []
        params = []
        if username is not None:
            update_fields.append("username = %s")
            params.append(new_username)
        if email is not None:
            update_fields.append("email = %s")
            params.append(new_email)
        if new_role_id is not None:
            update_fields.append("role_id = %s")
            params.append(new_role_id)

        if update_fields:
            params.append(target_user_id)
            cursor.execute(
                f'''
                UPDATE public."Users"
                SET {", ".join(update_fields)}
                WHERE user_id = %s
                ''',
                params
            )

            # Audit logging
            action = "USER_ROLE_CHANGED" if role_changed else "USER_UPDATED"
            log_user_audit(cursor, actor_id, action, target_user_id, ip_address)

            conn.commit()

        # Fetch updated record
        cursor.execute(
            '''
            SELECT u.user_id, u.username, u.email, r.role_name, u.status
            FROM public."Users" u
            JOIN public."Roles" r ON u.role_id = r.role_id
            WHERE u.user_id = %s
            ''',
            (target_user_id,)
        )
        updated_row = cursor.fetchone()

        return {
            "user_id": updated_row[0],
            "username": updated_row[1],
            "email": updated_row[2],
            "role": updated_row[3],
            "status": updated_row[4]
        }, None, 200

    except Error:
        if conn:
            conn.rollback()
        return None, "Database error", 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()