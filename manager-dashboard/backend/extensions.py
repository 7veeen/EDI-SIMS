import re
import urllib.parse
import psycopg2
from psycopg2 import pool
from config import DATABASE_URL


_connection_pool = None


def clean_database_url(url):
    """
    Cleans and safely percent-encodes special characters (such as @)
    in the password component of a postgresql connection URL.
    """
    if not url:
        return url
    url = url.strip().strip('"').strip("'")
    m = re.match(r'^(postgres(?:ql)?://)([^:]+):(.*)@([^@/:]+)(?::(\d+))?(/.*)$', url)
    if m:
        prefix, user, raw_password, host, port, db = m.groups()
        raw_password = urllib.parse.unquote(raw_password)
        encoded_password = urllib.parse.quote(raw_password, safe='')
        port_str = f':{port}' if port else ''
        return f'{prefix}{user}:{encoded_password}@{host}{port_str}{db}'
    return url


def get_connection_pool():
    global _connection_pool
    if _connection_pool is None:
        cleaned_url = clean_database_url(DATABASE_URL)
        if not cleaned_url or "[YOUR-PASSWORD]" in cleaned_url:
            raise ValueError("DATABASE_URL is not configured properly in .env.")
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=cleaned_url,
            connect_timeout=10
        )
    return _connection_pool


def get_db_connection():
    try:
        pool_instance = get_connection_pool()
        conn = pool_instance.getconn()
        return conn
    except Exception:
        cleaned_url = clean_database_url(DATABASE_URL)
        return psycopg2.connect(cleaned_url, connect_timeout=10)


def release_db_connection(conn):
    try:
        if _connection_pool and conn:
            _connection_pool.putconn(conn)
        elif conn:
            conn.close()
    except Exception:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def test_db_connection():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        return True, "Database connected successfully"
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            release_db_connection(conn)


def table_exists(cursor, table_name):
    """
    Checks if a table exists in public schema, case-insensitively.
    Returns the exact table name if found, else None.
    """
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND LOWER(table_name) = LOWER(%s)
        LIMIT 1;
    """, (table_name,))
    row = cursor.fetchone()
    return row[0] if row else None
