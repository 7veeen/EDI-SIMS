import os
import sys
import threading
import unittest
from decimal import Decimal
import psycopg2

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.extensions import (
    ConnectionPoolManager,
    PooledConnectionProxy,
    PoolExhaustedError,
    get_db_connection,
    release_request_connection
)
from psycopg2.extensions import TRANSACTION_STATUS_IDLE


class ConnectionPoolingTestCase(unittest.TestCase):
    """
    Focused verification test suite for SIMS Database Connection Pooling and Request-Scoped Lifecycle.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_pool_manager_singleton(self):
        """Verify ConnectionPoolManager behaves as a thread-safe singleton."""
        mgr1 = ConnectionPoolManager.get_instance()
        mgr2 = ConnectionPoolManager.get_instance()
        self.assertIs(mgr1, mgr2)
        self.assertIsNotNone(mgr1._pool)

    def test_02_standalone_connection_checkout_and_return(self):
        """Verify outside request context, connection is returned to pool on conn.close()."""
        conn = get_db_connection()
        self.assertIsInstance(conn, PooledConnectionProxy)
        self.assertEqual(conn.closed, 0)

        cur = conn.cursor()
        cur.execute("SELECT 1 AS num")
        row = cur.fetchone()
        self.assertEqual(row[0], 1)
        cur.close()

        conn.close()
        self.assertEqual(conn.closed, 1)

    def test_03_request_scoped_connection_reuse(self):
        """Verify that within an active Flask request context, multiple get_db_connection calls reuse the same physical connection."""
        with self.app.test_request_context("/api/test-scoped"):
            conn1 = get_db_connection()
            cur1 = conn1.cursor()
            cur1.execute("SELECT 42")
            val1 = cur1.fetchone()[0]
            cur1.close()
            conn1.close()  # Proxy closed, but raw connection remains in request

            self.assertEqual(conn1.closed, 1)

            # Second call in same request context
            conn2 = get_db_connection()
            self.assertEqual(conn2.closed, 0)
            self.assertIs(conn1._raw_conn, conn2._raw_conn, "Expected identical underlying physical connection")

            cur2 = conn2.cursor()
            cur2.execute("SELECT 84")
            val2 = cur2.fetchone()[0]
            cur2.close()
            conn2.close()

            self.assertEqual(val1, 42)
            self.assertEqual(val2, 84)

            # Simulate request teardown
            release_request_connection()

    def test_04_rollback_on_proxy_close_resets_transaction(self):
        """Verify that if a read query opened a transaction, conn.close() rolls it back to IDLE."""
        with self.app.test_request_context("/api/test-rollback"):
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()

            # Transaction is active/in transaction
            self.assertNotEqual(conn._raw_conn.get_transaction_status(), TRANSACTION_STATUS_IDLE)

            # Close proxy
            conn.close()

            # Physical connection transaction should now be rolled back to IDLE
            self.assertEqual(conn._raw_conn.get_transaction_status(), TRANSACTION_STATUS_IDLE)

            release_request_connection()

    def test_05_teardown_exception_rollback(self):
        """Verify request teardown with an exception rolls back uncommitted transactions before pool return."""
        with self.app.test_request_context("/api/test-exception"):
            conn = get_db_connection()
            raw_conn = conn._raw_conn

            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()

            self.assertNotEqual(raw_conn.get_transaction_status(), TRANSACTION_STATUS_IDLE)

            # Teardown with simulated exception
            release_request_connection(exception=RuntimeError("Simulated failure"))

            self.assertEqual(raw_conn.get_transaction_status(), TRANSACTION_STATUS_IDLE)

    def test_06_context_manager_commit_and_rollback(self):
        """Verify context manager semantics: commit on success, rollback on error."""
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 99")
            val = cur.fetchone()[0]
            cur.close()
            self.assertEqual(val, 99)

        try:
            with get_db_connection() as conn_err:
                cur = conn_err.cursor()
                cur.execute("SELECT 100")
                cur.close()
                raise ValueError("Context manager test error")
        except ValueError:
            pass

    def test_07_pool_exhaustion_explicit_handling(self):
        """Verify that when pool is exhausted, PoolExhaustedError is raised and 503 is returned."""
        test_pool = ConnectionPoolManager(minconn=1, maxconn=1)
        try:
            conn1 = test_pool.get_connection()
            with self.assertRaises(PoolExhaustedError):
                test_pool.get_connection()
            test_pool.return_connection(conn1)
        finally:
            test_pool.close_all()

    def test_08_concurrent_threads_pool_safety(self):
        """Verify concurrent multi-threaded checkouts execute safely without deadlock or corruption."""
        results = []
        errors = []

        def worker(idx):
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("SELECT %s", (idx,))
                res = cur.fetchone()[0]
                cur.close()
                conn.close()
                results.append(res)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors in concurrent worker threads: {errors}")
        self.assertEqual(len(results), 5)
        self.assertEqual(sorted(results), [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
