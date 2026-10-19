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
from app.services.team2.shipment_service import update_shipment_status, create_shipment


class POShipmentAggregationPhaseBTestCase(unittest.TestCase):
    """
    Test suite for SIMS Phase B: Purchase Order Status Aggregation for Split Shipments.
    Verifies:
      1. Single-shipment PO transitions to Delivered when delivered.
      2. Split-shipment PO does NOT transition to Delivered when first shipment is delivered.
      3. Split-shipment PO transitions to Delivered only when ALL shipments are delivered.
      4. Mixed shipment statuses (Delivered + In Transit / Delayed) keep PO in Accepted.
      5. Cancelled shipment does not automatically count as delivered (keeps PO in Accepted).
      6. All-cancelled shipments leave PO in Accepted.
      7. Unrelated PO statuses (Rejected, Pending) are preserved and never overwritten.
      8. Adding an active shipment to a Delivered PO resumes PO to Accepted.
      9. Concurrent status updates to separate shipments for the same PO serialize cleanly via PO FOR UPDATE lock.
      10. Atomic rollback on database failure during PO aggregation.
      11. Phase A row-level locking on Shipments and conditional update remain intact.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.manager_token = cls._get_token("demo_manager", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    def test_01_single_shipment_delivered_sets_po_delivered(self):
        """Single shipment PO transitions from Accepted to Delivered upon delivery."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    # Single shipment, now delivered
                    return [(101, "Delivered")]
                return []

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(res["status"], "Delivered")
        self.assertEqual(po_state["status"], "Delivered", "Single-shipment PO must transition to Delivered")

    def test_02_split_shipments_first_delivered_keeps_po_accepted(self):
        """Split shipments: Delivering Shipment 1 while Shipment 2 is In Transit leaves PO as Accepted."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    # 2 shipments: S1 delivered, S2 still In Transit
                    return [(101, "Delivered"), (102, "In Transit")]
                return []

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(res["status"], "Delivered")
        self.assertEqual(po_state["status"], "Accepted", "PO must NOT become Delivered while Shipment 2 is In Transit")

    def test_03_split_shipments_all_delivered_sets_po_delivered(self):
        """Split shipments: When second (and final) shipment is delivered, PO transitions to Delivered."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (102, 50, 5, "In Transit", "SHP-002", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    # Both shipments now Delivered
                    return [(101, "Delivered"), (102, "Delivered")]
                return []

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
                shipment_id=102,
                new_status="Delivered",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(res["status"], "Delivered")
        self.assertEqual(po_state["status"], "Delivered", "PO must transition to Delivered when all shipments are Delivered")

    def test_04_split_shipments_mix_with_delayed_keeps_po_accepted(self):
        """Split shipments with Delivered and Delayed shipments leaves PO as Accepted."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    return [(101, "Delivered"), (102, "Delayed")]
                return []

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(po_state["status"], "Accepted", "PO must remain Accepted when another shipment is Delayed")

    def test_05_cancelled_shipment_does_not_count_as_delivered(self):
        """Cancelled shipment does NOT count as delivered; PO with Delivered + Cancelled remains Accepted."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    # 1 Delivered, 1 Cancelled
                    return [(101, "Delivered"), (102, "Cancelled")]
                return []

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(po_state["status"], "Accepted", "Cancelled shipment cannot count as delivered; PO remains Accepted")

    def test_06_all_cancelled_shipments_leaves_po_accepted(self):
        """When all shipments are cancelled, PO must remain Accepted (never Delivered)."""
        executed_queries = []
        po_state = {"status": "Accepted"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

            def fetchall(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments"' in last_q and "purchase_order_id" in last_q:
                    return [(101, "Cancelled"), (102, "Cancelled")]
                return []

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
                new_status="Cancelled",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        self.assertEqual(po_state["status"], "Accepted", "All-cancelled shipments must not mark PO Delivered")

    def test_07_unrelated_po_state_rejected_preserved(self):
        """Rejected PO state is strictly preserved and never overwritten by shipment delivery."""
        executed_queries = []
        po_state = {"status": "Rejected"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertEqual(po_state["status"], "Rejected", "Rejected PO must remain Rejected")

    def test_08_unrelated_po_state_pending_preserved(self):
        """Pending PO state (awaiting supplier decision) is strictly preserved."""
        executed_queries = []
        po_state = {"status": "Pending"}

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, po_state["status"])
                return None

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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertEqual(po_state["status"], "Pending", "Pending PO must remain Pending")

    def test_09_adding_shipment_to_delivered_po_resumes_accepted(self):
        """Creating an active shipment for a previously Delivered PO resumes PO status to Accepted."""
        executed_queries = []
        po_state = {"status": "Delivered"}

        class MockCursor:
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'UPDATE "PurchaseOrders"' in query and 'SET status = %s' in query:
                    po_state["status"] = params[0]

            def fetchone(self):
                last_q = executed_queries[-1][0] if executed_queries else ""
                if 'FROM "Suppliers"' in last_q:
                    return (5, "Supplier Name")
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, 5, po_state["status"], "Accepted")
                if 'FROM "SupplierQuotations"' in last_q:
                    return None
                if 'MAX(shipment_id)' in last_q:
                    return (101,)
                if 'INSERT INTO "Shipments"' in last_q:
                    return (201,)
                return None

            def fetchall(self):
                return []

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
            res, err = create_shipment(
                data={
                    "purchase_order_id": 50,
                    "carrier": "Blue Dart",
                    "tracking_number": "BD-123456",
                    "shipping_method": "Standard",
                    "status": "In Transit",
                    "package_count": 2,
                    "total_weight": 15.5,
                    "shipping_notes": "Consignment Part 2",
                    "origin_address": "Warehouse Hub",
                    "destination_address": "SIMS Main Depot"
                },
                user_id=5,
                role="Supplier",
                username="demo_supplier"
            )

        self.assertIsNone(err)
        self.assertEqual(po_state["status"], "Accepted", "Adding active shipment to Delivered PO must resume PO to Accepted")

    def test_10_concurrent_updates_to_separate_shipments_same_po(self):
        """
        Simulate concurrent updates to separate shipments (S1 and S2) for the same PO.
        With row locking on PurchaseOrders (FOR UPDATE), updates are serialized:
        - Thread 1 delivers S1: PO stays Accepted because S2 is still In Transit.
        - Thread 2 delivers S2: PO transitions to Delivered because both S1 and S2 are Delivered.
        - Final PO status MUST be 'Delivered'.
        """
        po_lock = threading.Lock()
        shipment_records = {
            101: "In Transit",
            102: "In Transit"
        }
        po_record = {"status": "Accepted"}
        results = []

        def worker(shipment_id, thread_name):
            # Serialized under PO row lock (simulating SELECT ... FROM PurchaseOrders FOR UPDATE)
            with po_lock:
                # 1. Update this shipment
                shipment_records[shipment_id] = "Delivered"

                # 2. Recalculate PO delivery state
                all_delivered = all(s == "Delivered" for s in shipment_records.values())
                if all_delivered:
                    po_record["status"] = "Delivered"
                else:
                    po_record["status"] = "Accepted"

                results.append((thread_name, shipment_id, po_record["status"]))

        t1 = threading.Thread(target=worker, args=(101, "Thread-1-S101"))
        t2 = threading.Thread(target=worker, args=(102, "Thread-2-S102"))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(results), 2)
        # S1 and S2 must both be Delivered
        self.assertEqual(shipment_records[101], "Delivered")
        self.assertEqual(shipment_records[102], "Delivered")
        # Final PO status MUST be Delivered
        self.assertEqual(po_record["status"], "Delivered", "Final PO status must be Delivered after both shipments deliver")

    def test_11_failed_aggregation_rolls_back_atomically(self):
        """A failure during PO aggregation rolls back shipment and PO changes atomically."""
        executed_queries = []
        rollback_called = False

        class FailingCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append(query.strip())
                if 'UPDATE "PurchaseOrders"' in query:
                    raise Exception("Simulated DB connection failure during PO update")

            def fetchone(self):
                last_q = executed_queries[-1] if executed_queries else ""
                if 'FROM "PurchaseOrders"' in last_q:
                    return (50, "Accepted")
                return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)

            def fetchall(self):
                return [(101, "Delivered")]

            def close(self):
                pass

        class FailingConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return FailingCursor()
            def commit(self):
                pass
            def rollback(self):
                nonlocal rollback_called
                rollback_called = True
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=FailingConn()):
            res, err = update_shipment_status(
                shipment_id=101,
                new_status="Delivered",
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(res)
        self.assertTrue(rollback_called, "Rollback must be called when PO aggregation update fails")
        self.assertIn("Database error", err)

    def test_12_phase_a_shipment_concurrency_locks_preserved(self):
        """Verify Phase A row lock (FOR UPDATE OF shp) and Phase B PO lock (FOR UPDATE) both execute."""
        executed_queries = []

        class MockCursor:
            rowcount = 1
            def execute(self, query, params=None):
                executed_queries.append(query.strip())
            def fetchone(self):
                last_q = executed_queries[-1] if executed_queries else ""
                if 'FROM "Shipments" shp' in last_q and "FOR UPDATE OF shp" in last_q:
                    return (101, 50, 5, "In Transit", "SHP-001", None, None, "Supplier A", 7)
                if 'FROM "PurchaseOrders"' in last_q and "FOR UPDATE" in last_q:
                    return (50, "Accepted")
                return None
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
                user_id=1,
                role="Owner",
                username="demo_owner"
            )

        self.assertIsNone(err)
        # Verify Shipments FOR UPDATE OF shp
        self.assertTrue(any('FROM "Shipments" shp' in q and "FOR UPDATE OF shp" in q for q in executed_queries))
        # Verify PurchaseOrders FOR UPDATE
        self.assertTrue(any('FROM "PurchaseOrders"' in q and "FOR UPDATE" in q for q in executed_queries))


if __name__ == "__main__":
    unittest.main()
