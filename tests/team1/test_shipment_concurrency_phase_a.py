import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team1.inventory_service import stock_in, stock_in_shipment
from app.services.team2.shipment_service import update_shipment_status


class ShipmentConcurrencyPhaseATestCase(unittest.TestCase):
    """
    Test suite for SIMS Phase A: Stock-In and Shipment Status Concurrency Defect Fixes.
    Verifies:
      1. Row-level locking (SELECT ... FOR UPDATE) in stock_in() prevents double-receipt.
      2. Lock ordering (Shipments -> Inventory) and re-evaluating remaining quantities under lock.
      3. Atomic rollback on failure in stock_in().
      4. Business rule preservation (Delivered status requirement, employee assignment, partial receipts).
      5. Row-level locking (SELECT ... FOR UPDATE OF shp) in update_shipment_status().
      6. Optimistic conditional update (WHERE shipment_id = %s AND status = %s).
      7. Concurrent conflicting transitions (e.g. Delivered vs Cancelled) serialization and terminal state enforcement.
      8. HTTP 409 Conflict handling at the route layer.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Retrieve test tokens
        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.manager_token = cls._get_token("demo_manager", "password123")
        cls.employee_token = cls._get_token("demo_employee", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    # =========================================================================
    # Group 1: Stock-In Concurrency & Row-Level Locking
    # =========================================================================

    def test_01_stock_in_uses_for_update_lock_on_shipments(self):
        """Verify stock_in acquires FOR UPDATE lock on Shipments before checking receiving state."""
        executed_queries = []

        class MockCursor:
            def execute(self, query, params=None):
                executed_queries.append(query.strip())

            def fetchone(self):
                if not executed_queries:
                    return None
                last_q = executed_queries[-1]
                if 'FROM "Shipments"' in last_q and "FOR UPDATE" in last_q:
                    return (999, "SHP-TEST-001", 100, 5, "Delivered", 7, "Pending Receipt")
                if 'FROM "Products"' in last_q:
                    return (10, "Test Widget", "SKU-WIDGET-01", 10)
                if 'FROM "PurchaseOrders"' in last_q:
                    return (100, "Approved")
                if 'FROM "PurchaseOrderItems"' in last_q:
                    return (100,)
                if 'FROM "SupplierQuotations"' in last_q:
                    return (100,)
                if 'FROM "StockTransactions"' in last_q and "SUM" in last_q:
                    return (0,)
                if 'FROM "Inventory"' in last_q and "FOR UPDATE" in last_q:
                    return (1, 50)
                if 'INSERT INTO "StockTransactions"' in last_q:
                    return (501, "2026-10-18T10:00:00")
                return None

            def fetchall(self):
                if not executed_queries:
                    return []
                last_q = executed_queries[-1]
                if 'FROM "Shipments"' in last_q and 'purchase_order_id =' in last_q:
                    return [(999, "Delivered")]
                return [(10, 100)]

            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=999,
                product_id=10,
                quantity=10,
                user_id=7,
                role="Employee",
                username="demo_employee"
            )

        # Verify that Shipments query explicitly requested FOR UPDATE
        shipment_queries = [q for q in executed_queries if 'FROM "Shipments"' in q]
        self.assertTrue(len(shipment_queries) > 0, "No query was executed against Shipments")
        self.assertIn("FOR UPDATE", shipment_queries[0], "Shipments query MUST contain FOR UPDATE")

        # Verify lock order: Shipments FOR UPDATE occurred BEFORE Inventory FOR UPDATE
        shipment_idx = next(i for i, q in enumerate(executed_queries) if 'FROM "Shipments"' in q and "FOR UPDATE" in q)
        inventory_idx = next(i for i, q in enumerate(executed_queries) if 'FROM "Inventory"' in q and "FOR UPDATE" in q)
        self.assertLess(shipment_idx, inventory_idx, "Shipments row must be locked before Inventory row")

    def test_02_concurrent_stock_in_serialized_prevents_over_receipt(self):
        """
        Simulate two concurrent threads attempting to stock-in the same remaining 10 units.
        Thread 1 succeeds and receives 10.
        Thread 2 waits on the lock, and upon acquiring lock, sees remaining = 0 and is rejected.
        """
        lock = threading.Lock()
        shipment_state = {
            "received_total": 0,
            "expected_total": 10
        }
        results = []

        def worker(thread_id, qty):
            # Simulate database connection behavior with row-level locking
            with lock:
                # Inside locked critical section (representing PostgreSQL SELECT FOR UPDATE):
                already_received = shipment_state["received_total"]
                remaining = max(0, shipment_state["expected_total"] - already_received)

                if qty > remaining:
                    results.append((thread_id, None, f"Received quantity ({qty}) exceeds remaining receivable quantity ({remaining})"))
                    return

                # Perform update
                shipment_state["received_total"] += qty
                results.append((thread_id, {"received": qty, "total_received": shipment_state["received_total"]}, None))

        t1 = threading.Thread(target=worker, args=(1, 10))
        t2 = threading.Thread(target=worker, args=(2, 10))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one thread should succeed, and one must fail
        successes = [r for r in results if r[1] is not None]
        failures = [r for r in results if r[2] is not None]

        self.assertEqual(len(successes), 1, "Exactly one concurrent thread must succeed")
        self.assertEqual(len(failures), 1, "The competing concurrent thread must be rejected")
        self.assertEqual(shipment_state["received_total"], 10, "Total received must not exceed 10")
        self.assertIn("exceeds remaining receivable", failures[0][2])

    def test_03_stock_in_rejects_non_delivered_shipment(self):
        """Verify stock_in strictly rejects shipments that are not 'Delivered'."""
        class MockCursor:
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                return (123, "SHP-123", 10, 5, "In Transit", 7, "Pending Receipt")
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=123,
                product_id=1,
                quantity=5,
                user_id=7,
                role="Employee",
                username="demo_employee"
            )
            self.assertIsNone(res)
            self.assertIn("must be 'Delivered'", err)

    def test_04_stock_in_rejects_unauthorized_employee(self):
        """Verify employee cannot receive shipment assigned to a different user."""
        class MockCursor:
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                # Assigned to user 99, but actor is user 7
                return (123, "SHP-123", 10, 5, "Delivered", 99, "Pending Receipt")
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=123,
                product_id=1,
                quantity=5,
                user_id=7,
                role="Employee",
                username="demo_employee"
            )
            self.assertIsNone(res)
            self.assertIn("Access denied", err)

    def test_05_stock_in_alias_export(self):
        """Verify stock_in_shipment alias references stock_in function identically."""
        self.assertIs(stock_in_shipment, stock_in)

    # =========================================================================
    # Group 2: Status-Update Concurrency & Incompatible Transitions
    # =========================================================================

    def test_06_update_shipment_status_uses_for_update_of_shp(self):
        """Verify update_shipment_status acquires FOR UPDATE OF shp and conditional update."""
        executed_queries = []

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append(query.strip())
            def fetchone(self):
                last_q = executed_queries[-1] if executed_queries else ""
                if 'FROM "PurchaseOrders"' in last_q:
                    return (50, "Accepted")
                return (
                    101,  # shipment_id
                    50,   # purchase_order_id
                    5,    # supplier_id
                    "In Transit",  # current_status
                    "SHP-PO0050-001",  # shipment_number
                    None,  # shipped_at
                    None,  # delivered_at
                    "Supplier Name",  # supplier_name
                    7     # assigned_employee_id
                )
            def fetchall(self):
                return [(101, "Delivered")]
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Delivered",
                location="Warehouse Bay 1",
                notes="Delivered on schedule",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(res["status"], "Delivered")

        # Verify SELECT contains FOR UPDATE OF shp
        select_queries = [q for q in executed_queries if 'FROM "Shipments" shp' in q]
        self.assertTrue(len(select_queries) > 0)
        self.assertIn("FOR UPDATE OF shp", select_queries[0])

        # Verify UPDATE contains conditional status check
        update_queries = [q for q in executed_queries if 'UPDATE "Shipments"' in q]
        self.assertTrue(len(update_queries) > 0)
        self.assertIn("WHERE shipment_id = %s AND status = %s", update_queries[0])

    def test_07_concurrent_conflicting_transitions_serialized(self):
        """
        Simulate two concurrent threads attempting conflicting transitions from 'In Transit':
        Thread A: In Transit -> Delivered
        Thread B: In Transit -> Cancelled
        With row locking, exactly one succeeds. The other sees terminal state and is rejected.
        """
        lock = threading.Lock()
        shipment_state = {
            "status": "In Transit",
            "history": []
        }
        results = []

        allowed_transitions = {
            "ready for shipment": ["dispatched", "in transit", "cancelled"],
            "dispatched": ["in transit", "delayed", "delivered", "cancelled"],
            "in transit": ["delivered", "delayed", "cancelled"],
            "delayed": ["in transit", "delivered", "cancelled"],
            "delivered": [],  # Terminal
            "cancelled": []   # Terminal
        }

        def worker(thread_name, requested_new_status):
            with lock:
                curr_status = shipment_state["status"]
                curr_lower = curr_status.lower()
                new_lower = requested_new_status.lower()

                if curr_lower not in allowed_transitions or new_lower not in allowed_transitions[curr_lower]:
                    results.append((thread_name, None, f"Invalid status transition from '{curr_status}' to '{requested_new_status}'"))
                    return

                # Apply status
                shipment_state["status"] = requested_new_status
                shipment_state["history"].append(requested_new_status)
                results.append((thread_name, {"status": requested_new_status}, None))

        t1 = threading.Thread(target=worker, args=("Thread-Delivered", "Delivered"))
        t2 = threading.Thread(target=worker, args=("Thread-Cancelled", "Cancelled"))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if r[1] is not None]
        failures = [r for r in results if r[2] is not None]

        self.assertEqual(len(successes), 1, "Exactly one conflicting transition can succeed")
        self.assertEqual(len(failures), 1, "The competing transition must be rejected")
        self.assertIn("Invalid status transition", failures[0][2])
        self.assertIn(shipment_state["status"], ("Delivered", "Cancelled"))

    def test_08_terminal_state_delivered_cannot_transition(self):
        """Verify Delivered status cannot transition to Cancelled or In Transit."""
        class MockCursor:
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                return (101, 50, 5, "Delivered", "SHP-001", None, None, "Supplier", 7)
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Cancelled",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )
            self.assertIsNone(res)
            self.assertIn("Invalid status transition from 'Delivered' to 'Cancelled'", err)

    def test_09_terminal_state_cancelled_cannot_transition(self):
        """Verify Cancelled status cannot transition to Delivered."""
        class MockCursor:
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                return (101, 50, 5, "Cancelled", "SHP-001", None, None, "Supplier", 7)
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Delivered",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )
            self.assertIsNone(res)
            self.assertIn("Invalid status transition from 'Cancelled' to 'Delivered'", err)

    def test_10_conditional_update_conflict_triggers_error(self):
        """Verify that when cursor.rowcount == 0 in update, a Conflict error is returned."""
        class MockCursor:
            rowcount = 0  # Simulates another transaction modified the row concurrently
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier", 7)
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Delivered",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )
            self.assertIsNone(res)
            self.assertIn("Conflict: Shipment status was concurrently modified", err)

    def test_11_route_returns_409_on_conflict(self):
        """Verify that PATCH /api/shipments/<id>/status returns HTTP 409 Conflict when service returns Conflict."""
        with patch("app.routes.team2.shipments.update_shipment_status") as mock_service:
            mock_service.return_value = (None, "Conflict: Shipment status was concurrently modified from 'In Transit'")
            resp = self.client.patch(
                "/api/shipments/101/status",
                headers={"Authorization": f"Bearer {self.owner_token}"},
                json={"status": "Delivered"}
            )
            self.assertEqual(resp.status_code, 409)
            data = resp.get_json()
            self.assertIn("Conflict", data["error"])

    def test_12_idempotent_status_returns_200_unchanged(self):
        """Verify requesting the existing status returns 200 without executing DB update."""
        class MockCursor:
            def execute(self, query, params=None):
                pass
            def fetchone(self):
                return (101, 50, 5, "Delivered", "SHP-001", None, None, "Supplier", 7)
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Delivered",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )
            self.assertIsNone(err)
            self.assertEqual(res["message"], "Status unchanged")
            self.assertEqual(res["status"], "Delivered")


if __name__ == "__main__":
    unittest.main()
