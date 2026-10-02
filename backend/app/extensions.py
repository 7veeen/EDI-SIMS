import os
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from app.config import DATABASE_URL

# Initialize a global connection pool
try:
    db_pool = ThreadedConnectionPool(1, 20, DATABASE_URL)
except Exception as e:
    print("Error initializing connection pool:", e)
    db_pool = None

class PooledConnectionWrapper:
    def __init__(self, conn, pool):
        self._conn = conn
        self._pool = pool
        
    def __getattr__(self, item):
        return getattr(self._conn, item)
        
    def close(self):
        if self._pool and self._conn:
            self._pool.putconn(self._conn)
            self._conn = None

def get_db_connection():
    if db_pool:
        conn = db_pool.getconn()
        return PooledConnectionWrapper(conn, db_pool)
    return psycopg2.connect(DATABASE_URL)