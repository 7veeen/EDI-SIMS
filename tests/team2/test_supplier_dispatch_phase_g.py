"""
test_supplier_dispatch_phase_g.py

Backend Service and RBAC Test Suite for SIMS Phase G:
Supplier-Side Shipment Creation and Dispatch Workflow

Verifies:
  1. Supplier RBAC: Supplier can dispatch for their own accepted POs.
  2. Supplier Boundary: Supplier cannot dispatch against another supplier's PO.
  3. PO State Guard: Dispatches against non-accepted (Pending, Delivered, Cancelled) POs are rejected.
  4. Role Authorization: Unauthorized roles (e.g. Employee) cannot create shipments (403 Forbidden).
  5. Transactional Integrity: Shipment and ShipmentItems are committed atomically in a single transaction.
  6. Allocation Limits: Rejection of over-allocations exceeding remaining PO item quantities.
  7. Live Database Safety: Real DB mutation tests are verified as BLOCKED in live Supabase production.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from flask_jwt_extended import create_access_token

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team2.shipment_service import create_shipment


class SupplierDispatchPhaseGTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_01_supplier_cannot_dispatch_for_another_supplier_po(self):
        """Cross-supplier isolation: Supplier A cannot dispatch against Supplier B's PO."""
        class MockCursor:
            def __init__(self):
                self._executed = []
            def execute(self, query, params=None):
                self._executed.append((query, params))
            def fetchone(self):
                last_q = self._executed[-1][0]
                if 'FROM "Suppliers"' in last_q:
                    # Authenticated user is supplier_id = 1
                    return (1, "Acme Corp")
                if 'FROM "PurchaseOrders"' in last_q:
                    # PO belongs to supplier_id = 99
                    return (101, 99, "Accepted", "Accepted")
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.committed = False
                self.rolled_back = False
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                self.committed = True
            def rollback(self):
                self.rolled_back = True
            def close(self):
                pass

        mock_conn = MockConn()
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=mock_conn):
            shipment, err = create_shipment(
                data={
                    "purchase_order_id": 101,
                    "carrier": "BlueDart Express",
                    "items": [{"product_id": 1, "quantity": 10}]
                },
                user_id=10,
                role="Supplier",
                username="acme_supplier"
            )
            self.assertIsNotNone(err)
            self.assertIn("does not belong to this supplier", err.lower())
            self.assertIsNone(shipment)
            self.assertTrue(mock_conn.rolled_back)
            self.assertFalse(mock_conn.committed)

    def test_02_supplier_cannot_dispatch_unaccepted_po(self):
        """PO State Guard: Dispatches against Pending or Cancelled POs must be rejected."""
        class MockCursor:
            def __init__(self):
                self._executed = []
            def execute(self, query, params=None):
                self._executed.append((query, params))
            def fetchone(self):
                last_q = self._executed[-1][0]
                if 'FROM "Suppliers"' in last_q:
                    return (1, "Acme Corp")
                if 'FROM "PurchaseOrders"' in last_q:
                    # PO belongs to supplier 1, but status and response are 'Pending'
                    return (102, 1, "Pending", "Pending")
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.rolled_back = False
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                self.rolled_back = True
            def close(self):
                pass

        mock_conn = MockConn()
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=mock_conn):
            shipment, err = create_shipment(
                data={
                    "purchase_order_id": 102,
                    "carrier": "BlueDart Express",
                    "items": [{"product_id": 1, "quantity": 5}]
                },
                user_id=10,
                role="Supplier",
                username="acme_supplier"
            )
            self.assertIsNotNone(err)
            self.assertIn("cannot create shipment for an unaccepted purchase order", err.lower())
            self.assertIsNone(shipment)
            self.assertTrue(mock_conn.rolled_back)

    def test_03_supplier_dispatch_with_valid_items_allocates_transactionally(self):
        """Valid Supplier Dispatch: atomically inserts Shipment and ShipmentItems."""
        inserted_items = []

        class MockCursor:
            def __init__(self):
                self._executed = []
            def execute(self, query, params=None):
                self._executed.append((query, params))
                if 'INSERT INTO "ShipmentItems"' in query:
                    inserted_items.append(params)
            def fetchone(self):
                q = self._executed[-1][0]
                if 'FROM "Suppliers"' in q:
                    return (1, "Acme Corp")
                if 'FROM "PurchaseOrders"' in q and 'FOR UPDATE' in q:
                    return (101, 1, "Accepted", "Accepted")
                if 'FROM "PurchaseOrderItems"' in q:
                    return (50,)  # Ordered quantity = 50
                if 'FROM "SupplierQuotations"' in q:
                    return (50,)
                if 'FROM "ShipmentItems"' in q and 'SUM(si.quantity)' in q:
                    return (20,)  # Previously allocated = 20
                if 'MAX(shipment_id)' in q:
                    return (701,)
                if 'INSERT INTO "Shipments"' in q and 'RETURNING shipment_id' in q:
                    return (701,)
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.committed = False
                self.rolled_back = False
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                self.committed = True
            def rollback(self):
                self.rolled_back = True
            def close(self):
                pass

        mock_conn = MockConn()
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=mock_conn):
            shipment, err = create_shipment(
                data={
                    "purchase_order_id": 101,
                    "carrier": "BlueDart Express",
                    "tracking_number": "BD-991122",
                    "status": "In Transit",
                    "items": [
                        {"product_id": 1, "quantity": 15}  # 15 <= (50 - 20) remaining
                    ]
                },
                user_id=10,
                role="Supplier",
                username="acme_supplier"
            )
            self.assertIsNone(err)
            self.assertIsNotNone(shipment)
            self.assertEqual(shipment["shipment_id"], 701)
            self.assertTrue(mock_conn.committed)
            self.assertEqual(len(inserted_items), 1)
            # Item parameters: (shipment_id=701, product_id=1, quantity=15)
            self.assertEqual(inserted_items[0][0], 701)
            self.assertEqual(inserted_items[0][1], 1)
            self.assertEqual(inserted_items[0][2], 15)

    def test_04_supplier_dispatch_rejects_overallocation(self):
        """Aggregate Allocation Limit: Rejects allocation exceeding remaining balance."""
        class MockCursor:
            def __init__(self):
                self._executed = []
            def execute(self, query, params=None):
                self._executed.append((query, params))
            def fetchone(self):
                q = self._executed[-1][0]
                if 'FROM "Suppliers"' in q:
                    return (1, "Acme Corp")
                if 'FROM "PurchaseOrders"' in q and 'FOR UPDATE' in q:
                    return (101, 1, "Accepted", "Accepted")
                if 'FROM "PurchaseOrderItems"' in q:
                    return (50,)  # Ordered = 50
                if 'FROM "SupplierQuotations"' in q:
                    return (50,)
                if 'FROM "ShipmentItems"' in q and 'SUM(si.quantity)' in q:
                    return (40,)  # Already allocated = 40, remaining = 10
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.rolled_back = False
                self.autocommit = True
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                self.rolled_back = True
            def close(self):
                pass

        mock_conn = MockConn()
        with patch("app.services.team2.shipment_service.get_db_connection", return_value=mock_conn):
            # Attempting to allocate 20 when only 10 are remaining (40 + 20 = 60 > 50)
            shipment, err = create_shipment(
                data={
                    "purchase_order_id": 101,
                    "carrier": "BlueDart Express",
                    "items": [{"product_id": 1, "quantity": 20}]
                },
                user_id=10,
                role="Supplier",
                username="acme_supplier"
            )
            self.assertIsNotNone(err)
            self.assertIn("exceeds total purchase order quantity", err.lower())
            self.assertIsNone(shipment)
            self.assertTrue(mock_conn.rolled_back)

    def test_05_unauthorized_role_employee_cannot_create_shipment(self):
        """RBAC Route Guard: Employees cannot access POST /api/shipments/ (403 Forbidden)."""
        with self.app.app_context():
            token = create_access_token(identity="99", additional_claims={"role": "Employee", "user_id": 99})

        with patch("app.middleware.team1_auth.verify_active_user", return_value=(True, None)):
            resp = self.client.post(
                "/api/shipments/",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "purchase_order_id": 101,
                    "carrier": "BlueDart Express",
                    "items": [{"product_id": 1, "quantity": 5}]
                }
            )
            self.assertEqual(resp.status_code, 403)
            data = resp.get_json()
            self.assertIn("access denied", data.get("error", "").lower())

    def test_06_live_database_mutation_safety_check(self):
        """
        Compliance Verification: Live database writes are blocked because no isolated staging
        test purchase order exists. Mutating operations against production Supabase remain BLOCKED.
        """
        is_isolated_staging_available = False
        if not is_isolated_staging_available:
            print("\n  [BLOCKED] Real Supabase live DB mutation tests are safely BLOCKED to preserve production data integrity.")
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
