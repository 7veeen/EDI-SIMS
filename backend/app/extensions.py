import atexit
import logging
import os
import threading
from flask import g, has_app_context, has_request_context
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from psycopg2.pool import ThreadedConnectionPool, PoolError

from app.config import DATABASE_URL

logger = logging.getLogger(__name__)


class PoolExhaustedError(Exception):
    """Raised when all connections in the database connection pool are in use."""
    pass


class ConnectionPoolManager:
    """
    Thread-safe connection pool manager for Supabase PostgreSQL.
    Maintains a single ThreadedConnectionPool across the application lifecycle.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, minconn=None, maxconn=None, dsn=None):
        if minconn is None:
            minconn = int(os.getenv("DB_POOL_MIN_CONN", "2"))
        if maxconn is None:
            maxconn = int(os.getenv("DB_POOL_MAX_CONN", "10"))

        self._minconn = minconn
        self._maxconn = maxconn
        self._dsn = dsn or DATABASE_URL
        self._pool = None
        self._pool_lock = threading.Lock()
        self._initialize_pool()

    def _initialize_pool(self):
        with self._pool_lock:
            if self._pool is None:
                if not self._dsn:
                    raise ValueError("DATABASE_URL is not configured.")
                try:
                    self._pool = ThreadedConnectionPool(
                        minconn=self._minconn,
                        maxconn=self._maxconn,
                        dsn=self._dsn
                    )
                    logger.info(
                        f"Database connection pool initialized (minconn={self._minconn}, maxconn={self._maxconn})."
                    )
                except Exception as e:
                    logger.error(f"Failed to initialize database connection pool: {e}")
                    raise

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_connection(self):
        """
        Check out a healthy connection from the pool.
        Raises PoolExhaustedError if the pool limit is reached.
        """
        if self._pool is None:
            self._initialize_pool()

        try:
            conn = self._pool.getconn()
        except PoolError as e:
            logger.error(f"Database connection pool exhausted (maxconn={self._maxconn}): {e}")
            raise PoolExhaustedError("Database connection pool exhausted. Please retry later.") from e

        # Validate that the checked-out connection is not closed or corrupted
        if getattr(conn, "closed", 1) != 0:
            logger.warning("Checked-out connection was closed; replacing with fresh connection.")
            try:
                self._pool.putconn(conn, close=True)
            except Exception:
                pass
            return self.get_connection()

        return conn

    def return_connection(self, conn, close=False):
        """
        Return a connection to the pool safely, ensuring transaction cleanups.
        """
        if self._pool is None or conn is None:
            return

        try:
            # If returning a healthy connection, ensure any uncommitted transaction is rolled back
            if not close and getattr(conn, "closed", 1) == 0:
                try:
                    if conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                        conn.rollback()
                except Exception as rb_err:
                    logger.warning(f"Error rolling back connection before pool return: {rb_err}")
                    close = True

                try:
                    conn.autocommit = False
                except Exception:
                    pass

            self._pool.putconn(conn, close=close)
        except Exception as put_err:
            logger.error(f"Error returning connection to pool: {put_err}")

    def close_all(self):
        """
        Safely terminate all pooled connections on application shutdown.
        """
        with self._pool_lock:
            if self._pool:
                try:
                    self._pool.closeall()
                    logger.info("Database connection pool closed successfully.")
                except Exception as close_err:
                    logger.error(f"Error closing database connection pool: {close_err}")
                finally:
                    self._pool = None


class PooledConnectionProxy:
    """
    Transparent proxy wrapping a pooled psycopg2 connection.
    - Inside a Flask request context: delegates .close() to local proxy cleanup and transaction rollback,
      while preserving the underlying physical connection for subsequent operations in the same request.
    - Outside a Flask request context (tests/scripts): returns connection to pool on .close().
    """

    def __init__(self, raw_conn, pool_mgr, request_scoped=False):
        self._raw_conn = raw_conn
        self._pool_mgr = pool_mgr
        self._request_scoped = request_scoped
        self._is_closed = False

    @property
    def closed(self):
        if self._is_closed:
            return 1
        return getattr(self._raw_conn, "closed", 0)

    @property
    def autocommit(self):
        return self._raw_conn.autocommit

    @autocommit.setter
    def autocommit(self, value):
        self._raw_conn.autocommit = value

    @property
    def status(self):
        return self._raw_conn.status

    def cursor(self, *args, **kwargs):
        if self.closed:
            raise psycopg2.InterfaceError("Connection is closed")
        return self._raw_conn.cursor(*args, **kwargs)

    def commit(self):
        if self.closed:
            raise psycopg2.InterfaceError("Connection is closed")
        return self._raw_conn.commit()

    def rollback(self):
        if self.closed:
            raise psycopg2.InterfaceError("Connection is closed")
        return self._raw_conn.rollback()

    def close(self):
        if self._is_closed:
            return
        self._is_closed = True

        if self._request_scoped:
            # Request-scoped proxy close: do not return to pool yet because subsequent
            # service/audit calls in this request may reuse the physical connection.
            # Clean up uncommitted read transaction so the connection is ready for the next call.
            try:
                if self._raw_conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                    self._raw_conn.rollback()
                self._raw_conn.autocommit = False
            except Exception:
                pass
        else:
            # Standalone connection outside request: return to pool immediately.
            self._pool_mgr.return_connection(self._raw_conn)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)


def init_db_pool(app=None):
    """
    Explicitly initialize the database connection pool during application creation.
    """
    return ConnectionPoolManager.get_instance()


def close_db_pool():
    """
    Close all connections in the database pool during application shutdown.
    """
    if ConnectionPoolManager._instance is not None:
        ConnectionPoolManager._instance.close_all()


# Register safe pool cleanup at process exit
atexit.register(close_db_pool)


def get_db_connection():
    """
    Acquire a database connection.
    - Inside a Flask context (app or request): retrieves or establishes a request-scoped pooled connection,
      ensuring that verify_active_user() and subsequent service operations reuse the same physical connection.
    - Outside request context: retrieves a connection from the pool and returns it upon conn.close().
    """
    pool_mgr = ConnectionPoolManager.get_instance()

    if has_app_context() or has_request_context():
        raw_conn = getattr(g, "_db_conn_raw", None)
        if raw_conn is None or getattr(raw_conn, "closed", 1) != 0:
            raw_conn = pool_mgr.get_connection()
            g._db_conn_raw = raw_conn
        return PooledConnectionProxy(raw_conn, pool_mgr, request_scoped=True)
    else:
        raw_conn = pool_mgr.get_connection()
        return PooledConnectionProxy(raw_conn, pool_mgr, request_scoped=False)


def release_request_connection(exception=None):
    """
    Teardown hook invoked at the end of each Flask request or application context.
    Ensures that any checked-out request connection is safely rolled back if necessary
    and returned to the pool exactly once.
    """
    try:
        raw_conn = getattr(g, "_db_conn_raw", None)
    except RuntimeError:
        raw_conn = None

    if raw_conn is not None:
        pool_mgr = ConnectionPoolManager.get_instance()
        try:
            # If request finished with exception or uncommitted transaction, roll back
            if exception is not None or raw_conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                try:
                    raw_conn.rollback()
                except Exception as rb_err:
                    logger.warning(f"Error rolling back connection on request teardown: {rb_err}")
            try:
                raw_conn.autocommit = False
            except Exception:
                pass
        finally:
            pool_mgr.return_connection(raw_conn, close=(getattr(raw_conn, "closed", 1) != 0))
            try:
                g._db_conn_raw = None
            except Exception:
                pass