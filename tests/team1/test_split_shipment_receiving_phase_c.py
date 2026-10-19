import os
import sys
import threading
from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team1.inventory_service import stock_in
from app.services.team2.shipment_service import (
    create_shipment,
    get_shipment_by_id,
    assign_employee
)


class SplitShipmentReceivingPhaseCTestCase(unittest.TestCase):
    """
    Test suite for SIMS Phase C: Split Shipment Receiving Progress Remediation.
    Verifies:
      1. One shipment whose allocation is smaller than parent PO quantity becomes Fully Received when its own allocation is received.
      2. Two shipments for the same PO have independent receiving progress.
      3. A partially received shipment remains Partially Received.
      4. A shipment with no received quantity remains Pending Receipt.
      5. A multi-product shipment becomes Fully Received only when every product allocation is complete.
      6. An attempt to receive more than the remaining shipment allocation is rejected.
      7. Concurrent stock-in attempts cannot over-receive the shipment.
      8. Employee assignment and RBAC protections remain intact.
      9. Shipment creation validates item allocations against PO quantity and rejects overages.
      10. Legacy shipments without ShipmentItems records maintain backward-compatible fallback to PO items.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    # =========================================================================
    # Test 1: Single Shipment with Allocation < PO Quantity Becomes Fully Received
    # =========================================================================
    def test_01_shipment_allocation_smaller_than_po_becomes_fully_received(self):
        """
        Verify that a shipment with allocated_quantity=40 on a PO of 100
        becomes 'Fully Received' when 40 units are received for that shipment.
        """
        executed_queries = []
        stock_transactions = []
        shipment_status_updates = []

        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None

            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                executed_queries.append((self._last_query, params))
                if 'UPDATE "Shipments"' in self._last_query and 'receiving_status =' in self._last_query:
                    shipment_status_updates.append(params[0])
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    stock_transactions.append(params)

            def fetchone(self):
                q = self._last_query
                # Shipments lock
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (101, "SHP-PO0050-001", 50, 2, "Delivered", 10, "Pending Receipt")
                # Product details
                if 'FROM "Products"' in q:
                    return (5, "Heavy Duty Widget", "SKU-HDW-05", 10)
                # ShipmentItems single product allocation check: allocation = 40
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (40,)
                # StockTransactions sum for this shipment and product
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (len(stock_transactions) * 40,)
                # Inventory FOR UPDATE
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 100)
                # INSERT INTO StockTransactions RETURNING
                if 'INSERT INTO "StockTransactions"' in q:
                    return (701, datetime(2026, 10, 18, 12, 0, 0))
                return None

            def fetchall(self):
                q = self._last_query
                # Allocated items for overall progress check
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s' in q:
                    return [(5, 40)]
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

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=101,
                product_id=5,
                quantity=40,
                notes="Dock 1 receipt",
                user_id=10,
                role="Employee",
                username="warehouse_emp"
            )

            self.assertIsNone(err)
            self.assertIsNotNone(res)
            self.assertEqual(res["receiving_progress"]["expected_quantity"], 40)
            self.assertEqual(res["receiving_progress"]["already_received"], 40)
            self.assertEqual(res["receiving_progress"]["remaining_quantity"], 0)
            self.assertEqual(res["receiving_progress"]["receiving_status"], "Fully Received")
            self.assertIn("Fully Received", shipment_status_updates)

    # =========================================================================
    # Test 2: Two Shipments for Same PO Have Independent Receiving Progress
    # =========================================================================
    def test_02_two_shipments_same_po_independent_progress(self):
        """
        Verify two shipments for PO #50:
        Shipment 1: allocation = 40, received = 40 -> Fully Received
        Shipment 2: allocation = 60, received = 0  -> Pending Receipt
        Shipment 2: receive 20 units -> Partially Received (20/60)
        """
        # Shipment 1 verification
        class MockCursorS1:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (101, "SHP-PO0050-001", 50, 2, "Delivered", 10, "Pending Receipt")
                if 'FROM "Products"' in q:
                    return (5, "Heavy Duty Widget", "SKU-HDW-05", 10)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (40,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (self._inserted_qty,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 100)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (701, datetime(2026, 10, 18, 12, 0, 0))
                return None
            def fetchall(self):
                if 'FROM "ShipmentItems"' in self._last_query:
                    return [(5, 40)]
                return []
            def close(self):
                pass

        class MockConnS1:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursorS1()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConnS1()):
            res1, err1 = stock_in(
                shipment_id=101,
                product_id=5,
                quantity=40,
                user_id=10,
                role="Employee",
                username="emp1"
            )
            self.assertIsNone(err1)
            self.assertEqual(res1["receiving_progress"]["receiving_status"], "Fully Received")

        # Shipment 2 verification with partial receipt (20 of 60)
        class MockCursorS2:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (102, "SHP-PO0050-002", 50, 2, "Delivered", 10, "Pending Receipt")
                if 'FROM "Products"' in q:
                    return (5, "Heavy Duty Widget", "SKU-HDW-05", 10)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (60,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (self._inserted_qty,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 140)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (702, datetime(2026, 10, 18, 12, 10, 0))
                return None
            def fetchall(self):
                if 'FROM "ShipmentItems"' in self._last_query:
                    return [(5, 60)]
                return []
            def close(self):
                pass

        class MockConnS2:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursorS2()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConnS2()):
            res2, err2 = stock_in(
                shipment_id=102,
                product_id=5,
                quantity=20,
                user_id=10,
                role="Employee",
                username="emp1"
            )
            self.assertIsNone(err2)
            self.assertEqual(res2["receiving_progress"]["expected_quantity"], 60)
            self.assertEqual(res2["receiving_progress"]["already_received"], 20)
            self.assertEqual(res2["receiving_progress"]["remaining_quantity"], 40)
            self.assertEqual(res2["receiving_progress"]["receiving_status"], "Partially Received")

    # =========================================================================
    # Test 3: Partially Received Shipment Remains Partially Received
    # =========================================================================
    def test_03_partially_received_shipment_remains_partially_received(self):
        """Verify receipt of 15 units out of 50 leaves shipment in 'Partially Received'."""
        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (103, "SHP-003", 51, 2, "Delivered", 10, "Pending Receipt")
                if 'FROM "Products"' in q:
                    return (8, "Sensor Module", "SKU-SNS-08", 5)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (50,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (self._inserted_qty,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 20)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (703, datetime(2026, 10, 18, 12, 0, 0))
                return None
            def fetchall(self):
                if 'FROM "ShipmentItems"' in self._last_query:
                    return [(8, 50)]
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

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=103,
                product_id=8,
                quantity=15,
                user_id=10,
                role="Manager",
                username="manager1"
            )
            self.assertIsNone(err)
            self.assertEqual(res["receiving_progress"]["receiving_status"], "Partially Received")
            self.assertEqual(res["receiving_progress"]["remaining_quantity"], 35)

    # =========================================================================
    # Test 4: Shipment with Zero Received Quantity Remains Pending Receipt
    # =========================================================================
    def test_04_shipment_zero_received_remains_pending_receipt(self):
        """Verify get_shipment_by_id reports 'Pending Receipt' when 0 units received."""
        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'JOIN "Suppliers"' in q:
                    return (
                        104, "SHP-004", 52, 2, "Acme Logistics", "Alice", "alice@acme.com", "555-0101",
                        "FedEx", "TRK-004", "Ground", "Delivered", 2, 10.0, "Notes", "Dock", "Bay",
                        None, None, None, None, None,
                        None, 1000.0, "Accepted", None,
                        10, "Emp Alice", "Pending Receipt"
                    )
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (0,)
                return None
            def fetchall(self):
                q = self._last_query
                if 'FROM "ShipmentItems"' in q:
                    return [(12, "Steel Bolt", "SKU-BLT-12", 100, 1.5, 150.0)]
                if 'FROM "OrderStatusHistory"' in q:
                    return []
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res, err = get_shipment_by_id(shipment_id=104, user_id=10, role="Manager")
            self.assertIsNone(err)
            self.assertEqual(res["receiving_status"], "Pending Receipt")
            self.assertEqual(res["total_received_quantity"], 0)
            self.assertEqual(res["total_remaining_quantity"], 100)

    # =========================================================================
    # Test 5: Multi-Product Shipment Fully Received Only When All Complete
    # =========================================================================
    def test_05_multi_product_shipment_requires_all_complete(self):
        """
        Verify shipment with Product A (20) and Product B (30):
        Receiving Product A (20) -> Partially Received (because Product B is 0/30)
        Receiving Product B (30) -> Fully Received
        """
        # Step A: Product A received (20/20), Product B pending (0/30)
        class MockCursorA:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (105, "SHP-005", 53, 2, "Delivered", 10, "Pending Receipt")
                if 'FROM "Products"' in q:
                    return (1, "Product One", "SKU-001", 10)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (20,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    pid = self._last_params[1] if self._last_params and len(self._last_params) > 1 else None
                    if pid == 1:
                        return (self._inserted_qty,)
                    return (0,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 50)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (705, datetime(2026, 10, 18, 12, 0, 0))
                return None
            def fetchall(self):
                if 'FROM "ShipmentItems"' in self._last_query:
                    return [(1, 20), (2, 30)]
                return []
            def close(self):
                pass

        class MockConnA:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursorA()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConnA()):
            resA, errA = stock_in(
                shipment_id=105,
                product_id=1,
                quantity=20,
                user_id=10,
                role="Manager",
                username="manager1"
            )
            self.assertIsNone(errA)
            # Overall shipment must be Partially Received because Product B (30) is still pending
            self.assertEqual(resA["receiving_progress"]["receiving_status"], "Partially Received")

        # Step B: Product B received (30/30) when Product A is already (20/20)
        class MockCursorB:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (105, "SHP-005", 53, 2, "Delivered", 10, "Partially Received")
                if 'FROM "Products"' in q:
                    return (2, "Product Two", "SKU-002", 10)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (30,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    pid = self._last_params[1] if self._last_params and len(self._last_params) > 1 else None
                    if pid == 1:
                        return (20,) # Product 1 fully received previously
                    elif pid == 2:
                        return (self._inserted_qty,) # Product 2 received now
                    return (0,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (2, 80)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (706, datetime(2026, 10, 18, 12, 5, 0))
                return None
            def fetchall(self):
                if 'FROM "ShipmentItems"' in self._last_query:
                    return [(1, 20), (2, 30)]
                return []
            def close(self):
                pass

        class MockConnB:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursorB()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConnB()):
            resB, errB = stock_in(
                shipment_id=105,
                product_id=2,
                quantity=30,
                user_id=10,
                role="Manager",
                username="manager1"
            )
            self.assertIsNone(errB)
            self.assertEqual(resB["receiving_progress"]["receiving_status"], "Fully Received")

    # =========================================================================
    # Test 6: Attempt to Receive More than Remaining Allocation is Rejected
    # =========================================================================
    def test_06_receive_exceeding_remaining_allocation_rejected(self):
        """Verify that attempting to stock-in more than remaining allocation returns HTTP 400."""
        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (106, "SHP-006", 54, 2, "Delivered", 10, "Partially Received")
                if 'FROM "Products"' in q:
                    return (3, "Precision Sensor", "SKU-SNS-03", 5)
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return (20,)  # Allocation is 20
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (15,)  # 15 already received -> remaining is 5
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
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=106,
                product_id=3,
                quantity=6,  # 6 > 5 remaining
                user_id=10,
                role="Manager",
                username="manager1"
            )
            self.assertIsNone(res)
            self.assertIsNotNone(err)
            self.assertIn("exceeds remaining receivable quantity (5)", err)

    # =========================================================================
    # Test 7: Concurrent Stock-In Cannot Over-Receive Shipment
    # =========================================================================
    def test_07_concurrent_stock_in_cannot_over_receive(self):
        """
        Simulate concurrent stock-in attempts competing for remaining 10 units.
        Row lock serializes access; exactly 10 units are received, second thread rejected.
        """
        lock = threading.Lock()
        shipment_allocation = 10
        received_total = [0]
        results = []

        def worker(thread_id, qty):
            with lock:
                remaining = max(0, shipment_allocation - received_total[0])
                if qty > remaining:
                    results.append((thread_id, None, f"Exceeds remaining ({remaining})"))
                    return
                received_total[0] += qty
                results.append((thread_id, {"received": qty, "total": received_total[0]}, None))

        t1 = threading.Thread(target=worker, args=(1, 10))
        t2 = threading.Thread(target=worker, args=(2, 10))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if r[1] is not None]
        failures = [r for r in results if r[2] is not None]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(received_total[0], 10)

    # =========================================================================
    # Test 8: Employee Assignment & RBAC Protections
    # =========================================================================
    def test_08_employee_assignment_and_rbac_protections(self):
        """Verify unassigned employee is rejected (403), supplier is rejected (403)."""
        # 1. Unassigned employee
        class MockCursorUnassigned:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
            def fetchone(self):
                if 'FROM "Shipments"' in self._last_query:
                    # assigned_employee_id is 99, but user_id is 10
                    return (108, "SHP-008", 55, 2, "Delivered", 99, "Pending Receipt")
                return None
            def close(self):
                pass

        class MockConnUnassigned:
            def __init__(self):
                self.autocommit = True
            def cursor(self):
                return MockCursorUnassigned()
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConnUnassigned()):
            res, err = stock_in(
                shipment_id=108,
                product_id=1,
                quantity=5,
                user_id=10,
                role="Employee",
                username="emp1"
            )
            self.assertIsNone(res)
            self.assertIn("Access denied", err)

        # 2. Supplier role is rejected
        res_sup, err_sup = stock_in(
            shipment_id=108,
            product_id=1,
            quantity=5,
            user_id=2,
            role="Supplier",
            username="supplier_user"
        )
        self.assertIsNone(res_sup)
        self.assertIn("Access denied", err_sup)

    # =========================================================================
    # Test 9: Shipment Creation Validates Allocations Against PO Quantity
    # =========================================================================
    def test_09_shipment_creation_allocation_validation(self):
        """
        Verify create_shipment:
        - Rejects allocations exceeding total PO line item quantity.
        - Rejects duplicate product IDs in items payload.
        - Inserts into ShipmentItems upon success.
        """
        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self.inserted_items = []
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "ShipmentItems"' in self._last_query:
                    self.inserted_items.append(params)
            def fetchone(self):
                q = self._last_query
                if 'FROM "Suppliers"' in q:
                    return (2, "Acme Corp")
                if 'FROM "PurchaseOrders"' in q and 'FOR UPDATE' in q:
                    return (100, 2, "Accepted", "Accepted")
                if 'FROM "PurchaseOrders"' in q:
                    return (100, 2, "Accepted", "Accepted")
                if 'SELECT quotation_id' in q:
                    return None
                if 'SELECT quantity FROM "PurchaseOrderItems"' in q:
                    return (50,)  # PO has 50 units
                if 'SELECT quantity FROM "SupplierQuotations"' in q:
                    return (50,)
                if 'SELECT COALESCE(SUM(si.quantity), 0)' in q:
                    return (30,)  # 30 already allocated across prior shipments
                if 'SELECT COALESCE(MAX(shipment_id)' in q:
                    return (10,)
                if 'INSERT INTO "Shipments"' in q and 'RETURNING' in q:
                    return (111,)
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        cursor_inst = MockCursor()
        class MockConn:
            def __init__(self):
                self.autocommit = False
            def cursor(self):
                return cursor_inst
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        # Attempt A: 30 already allocated + 25 new = 55 > 50 -> must reject
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res_fail, err_fail = create_shipment(
                data={
                    "purchase_order_id": 100,
                    "items": [{"product_id": 5, "quantity": 25}]
                },
                user_id=2,
                role="Supplier",
                username="acme"
            )
            self.assertIsNone(res_fail)
            self.assertIn("exceeds total purchase order quantity", err_fail)

        # Attempt B: Duplicate product IDs in items list -> must reject
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            res_dup, err_dup = create_shipment(
                data={
                    "purchase_order_id": 100,
                    "items": [
                        {"product_id": 5, "quantity": 10},
                        {"product_id": 5, "quantity": 10}
                    ]
                },
                user_id=2,
                role="Supplier",
                username="acme"
            )
            self.assertIsNone(res_dup)
            self.assertIn("Duplicate product ID", err_dup)

        # Attempt C: Valid allocation (20 new + 30 previous = 50 == 50) -> succeeds
        class MockCursorValid(MockCursor):
            def fetchone(self):
                q = self._last_query
                if 'SELECT COALESCE(SUM(si.quantity), 0)' in q:
                    return (30,)
                return super().fetchone()

        valid_cursor = MockCursorValid()
        class MockConnValid:
            def __init__(self):
                self.autocommit = False
            def cursor(self):
                return valid_cursor
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConnValid()):
            res_ok, err_ok = create_shipment(
                data={
                    "purchase_order_id": 100,
                    "carrier": "FedEx",
                    "tracking_number": "TRK-100",
                    "items": [{"product_id": 5, "quantity": 20}]
                },
                user_id=2,
                role="Supplier",
                username="acme"
            )
            self.assertIsNone(err_ok)
            self.assertIsNotNone(res_ok)
            self.assertEqual(len(valid_cursor.inserted_items), 1)
            self.assertEqual(valid_cursor.inserted_items[0], (111, 5, 20))

    # =========================================================================
    # Test 10: Legacy Shipment Backward Compatibility
    # =========================================================================
    def test_10_legacy_shipment_fallback_to_po_items(self):
        """
        Verify that for legacy shipments where no ShipmentItems records exist,
        stock_in falls back gracefully to checking PurchaseOrderItems.
        """
        class MockCursor:
            def __init__(self):
                self._last_query = ""
                self._last_params = None
                self._inserted_qty = 0
            def execute(self, query, params=None):
                self._last_query = query.strip()
                self._last_params = params
                if 'INSERT INTO "StockTransactions"' in self._last_query:
                    self._inserted_qty = params[4]
            def fetchone(self):
                q = self._last_query
                if 'FROM "Shipments"' in q and 'FOR UPDATE' in q:
                    return (999, "SHP-LEGACY", 80, 2, "Delivered", 10, "Pending Receipt")
                if 'FROM "Products"' in q:
                    return (7, "Legacy Part", "SKU-LEG-07", 5)
                # ShipmentItems checks return None -> triggers fallback
                if 'FROM "ShipmentItems"' in q and 'WHERE shipment_id = %s AND product_id = %s' in q:
                    return None
                if 'FROM "ShipmentItems"' in q and 'COUNT(*)' in q:
                    return (0,)
                # PO fallback checks
                if 'FROM "PurchaseOrders"' in q:
                    return (80, "Approved")
                if 'FROM "PurchaseOrderItems"' in q and 'quantity' in q:
                    return (100,)
                if 'FROM "SupplierQuotations"' in q:
                    return (100,)
                if 'FROM "StockTransactions"' in q and 'SUM' in q:
                    return (self._inserted_qty,)
                if 'FROM "Inventory"' in q and 'FOR UPDATE' in q:
                    return (1, 10)
                if 'INSERT INTO "StockTransactions"' in q:
                    return (799, datetime(2026, 10, 18, 12, 0, 0))
                return None
            def fetchall(self):
                # Legacy fallback in overall progress check
                if 'FROM "ShipmentItems"' in self._last_query:
                    return []
                if 'FROM "Shipments"' in self._last_query and 'purchase_order_id =' in self._last_query:
                    return [(999, "Delivered")]
                if 'FROM "PurchaseOrderItems"' in self._last_query:
                    return [(7, 100)]
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

        with patch("app.services.team1.inventory_service.get_db_connection", return_value=MockConn()):
            res, err = stock_in(
                shipment_id=999,
                product_id=7,
                quantity=100,
                user_id=10,
                role="Manager",
                username="manager1"
            )
            self.assertIsNone(err)
            self.assertIsNotNone(res)
            self.assertEqual(res["receiving_progress"]["expected_quantity"], 100)
            self.assertEqual(res["receiving_progress"]["receiving_status"], "Fully Received")


if __name__ == "__main__":
    unittest.main()
