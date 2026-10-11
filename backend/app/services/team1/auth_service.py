from psycopg2 import Error
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import create_access_token

from app.extensions import get_db_connection


def login_user(username, password):
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
                u.password_hash,
                u.status,
                r.role_name
            FROM public."Users" u
            JOIN public."Roles" r
                ON u.role_id = r.role_id
            WHERE u.username = %s
            ''',
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            return None, "Invalid username or password"

        user_id = user[0]
        db_username = user[1]
        email = user[2]
        password_hash = user[3]
        status = user[4]
        role_name = user[5]

        if status != "Active":
            return None, "User account is inactive"

        if not check_password_hash(password_hash, password):
            return None, "Invalid username or password"

        access_token = create_access_token(
            identity=str(user_id),
            additional_claims={
                "username": db_username,
                "role": role_name
            }
        )
        # Audit Log: LOGIN on Users
        try:
            from app.services.team3.audit_service import log_audit_event
            log_audit_event(
                action='LOGIN',
                table_name='Users',
                record_id=user_id,
                user_id=user_id,
                cursor=cursor
            )
            conn.commit()
        except Exception as audit_err:
            print(f"[AUDIT WARNING] Failed to record login audit log: {audit_err}", flush=True)

        return {
            "access_token": access_token,
            "user": {
                "user_id": user_id,
                "username": db_username,
                "email": email,
                "role": role_name
            }
        }, None

    except Error:
        return None, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()

def change_password(user_id, current_password, new_password):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get the user's current password hash
        cursor.execute(
            '''
            SELECT password_hash
            FROM public."Users"
            WHERE user_id = %s
            ''',
            (user_id,)
        )

        user = cursor.fetchone()

        if user is None:
            return False, "User not found"

        current_password_hash = user[0]

        # Verify the current password
        if not check_password_hash(current_password_hash, current_password):
            return False, "Current password is incorrect"

        # Make sure the new password is different
        if check_password_hash(current_password_hash, new_password):
            return False, "New password must be different from the current password"

        # Hash the new password
        new_password_hash = generate_password_hash(new_password)

        # Update the password
        cursor.execute(
            '''
            UPDATE public."Users"
            SET password_hash = %s
            WHERE user_id = %s
            ''',
            (new_password_hash, user_id)
        )

        # Audit Log: PASSWORD_CHANGED on Users
        try:
            from app.services.team3.audit_service import log_audit_event
            log_audit_event(
                action='PASSWORD_CHANGED',
                table_name='Users',
                record_id=user_id,
                user_id=int(user_id),
                cursor=cursor
            )
        except Exception as audit_err:
            print(f"[AUDIT WARNING] Failed to record password change audit log: {audit_err}", flush=True)

        conn.commit()

        return True, None

    except Error:
        if conn:
            conn.rollback()

        return False, "Database error"

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()