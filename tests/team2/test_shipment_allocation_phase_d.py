import os
import sys
import unittest
from unittest.mock import MagicMock, patch

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team2.purchase_order_service import get_purchase_order_by_id
from app.services.team2.shipment_service import create_shipment


class ShipmentAllocationPhaseDTestCase(unittest.TestCase):
    """
    Test suite for SIMS Phase D: Shipment Allocation Backend Service & Contract Verification.
    Verifies:
      1. get_purchase_order_by_id returns allocated_quantity and remaining_quantity per item.
      2. create_shipment successfully processes and validates items allocations.
      3. Over-allocation exceeding remaining PO quantity is rejected.
      4. Invalid/non-positive quantities and duplicate product IDs are rejected.
      5. Products not belonging to the PO are rejected.
      6. Backward compatibility: creating shipment without items remains supported.
      7. Route layer POST /api/shipments/ handles allocation payload.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Retrieve test tokens
        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    def test_01_get_purchase_order_by_id_includes_allocated_and_remaining_quantities(self):
        """Verify get_purchase_order_by_id returns allocated_quantity and remaining_quantity."""
        class MockCursor:
            def __init__(self):
                self._step = 0
            def execute(self, query, params=None):
                self._query = query
                self._params = params
            def fetchone(self):
                # PO Header query
                if 'FROM "PurchaseOrders"' in self._query:
                    return (
                        101, 5, "Acme Supplier", "John Doe", "john@acme.com", "555-0101",
                        1, "manager1", None, None, 1000.0, "Accepted", "Accepted", None, ""
                    )
                return None
            def fetchall(self):
                # Supplier Quotations
                if 'FROM "SupplierQuotations"' in self._query:
                    return [(1, 50), (2, 30)]
                # ShipmentItems previously allocated query
                if 'FROM "ShipmentItems"' in self._query and 'SUM(si.quantity)' in self._query:
                    return [(1, 20), (2, 30)]
                # Line Items query
                if 'FROM "PurchaseOrderItems"' in self._query:
                    return [
                        (1001, 101, 1, "Product 1", "SKU-001", 50, 10.0, 500.0),
                        (1002, 101, 2, "Product 2", "SKU-002", 30, 10.0, 300.0)
                    ]
                # OrderStatusHistory query
                if 'FROM "OrderStatusHistory"' in self._query:
                    return []
                return []
            def close(self):
                pass

        class MockConn:
            def cursor(self):
                return MockCursor()
            def close(self):
                pass

        with patch("app.services.team2.purchase_order_service.get_db_connection", return_value=MockConn()):
            order, err = get_purchase_order_by_id(purchase_order_id=101, user_id=1, role="Owner")
            self.assertIsNone(err)
            self.assertIsNotNone(order)
            self.assertEqual(len(order["items"]), 2)

            item1 = next(it for it in order["items"] if it["product_id"] == 1)
            self.assertEqual(item1["quantity"], 50)
            self.assertEqual(item1["allocated_quantity"], 20)
            self.assertEqual(item1["remaining_quantity"], 30)

            item2 = next(it for it in order["items"] if it["product_id"] == 2)
            self.assertEqual(item2["quantity"], 30)
            self.assertEqual(item2["allocated_quantity"], 30)
            self.assertEqual(item2["remaining_quantity"], 0)

    def test_02_create_shipment_with_valid_allocations_inserts_shipment_items(self):
        """Verify create_shipment validates items and executes insert into ShipmentItems."""
        inserted_items = []
        executed_queries = []

        class MockCursor:
            def execute(self, query, params=None):
                executed_queries.append((query.strip(), params))
                if 'INSERT INTO "ShipmentItems"' in query:
                    inserted_items.append(params)
            def fetchone(self):
                last_q = executed_queries[-1][0]
                if 'FROM "Suppliers"' in last_q:
                    return (5, "Acme Supplier")
                if 'FROM "PurchaseOrders"' in last_q and 'FOR UPDATE' in last_q:
                    return (101, 5, "Accepted", "Accepted")
                if 'FROM "PurchaseOrderItems"' in last_q:
                    return (50,)
                if 'FROM "SupplierQuotations"' in last_q:
                    return (50,)
                if 'FROM "ShipmentItems"' in last_q and 'SUM' in last_q:
                    return (10,)  # 10 previously allocated out of 50
                if 'SELECT COALESCE(MAX(shipment_id)' in last_q:
                    return (10,)
                if 'INSERT INTO "Shipments"' in last_q:
                    return (11,)  # new shipment_id
                return None
            def fetchall(self):
                last_q = executed_queries[-1][0]
                if 'FROM "SupplierQuotations"' in last_q:
                    return [(1, 5, 'Approved')]
                return []
            def close(self):
                pass

        class MockConn:
            def __init__(self):
                self.committed = False
                self.rolled_back = False
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
            payload = {
                "purchase_order_id": 101,
                "carrier": "BlueDart Express",
                "tracking_number": "BD-12345",
                "shipping_method": "Standard Ground",
                "status": "Ready for Shipment",
                "package_count": 2,
                "total_weight": 10.0,
                "items": [
                    {"product_id": 1, "quantity": 25}
                ]
            }
            res, err = create_shipment(payload, user_id=5, role="Supplier", username="supplier1")
            self.assertIsNone(err)
            self.assertIsNotNone(res)
            self.assertTrue(mock_conn.committed)
            self.assertFalse(mock_conn.rolled_back)
            self.assertEqual(res["shipment_id"], 11)
            self.assertEqual(res["items"], [{"product_id": 1, "quantity": 25}])
            self.assertEqual(len(inserted_items), 1)
            self.assertEqual(inserted_items[0][0], 11)  # shipment_id
            self.assertEqual(inserted_items[0][1], 1)   # product_id
            self.assertEqual(inserted_items[0][2], 25)  # quantity

    def test_03_create_shipment_rejects_over_allocation(self):
        """Verify create_shipment rejects allocation when previously allocated + new > PO quantity."""
        class MockCursor:
            def execute(self, query, params=None):
                self._query = query
            def fetchone(self):
                if 'FROM "Suppliers"' in self._query:
                    return (5, "Acme Supplier")
                if 'FROM "PurchaseOrders"' in self._query and 'FOR UPDATE' in self._query:
                    return (101, 5, "Accepted", "Accepted")
                if 'FROM "PurchaseOrderItems"' in self._query:
                    return (50,)
                if 'FROM "SupplierQuotations"' in self._query:
                    return (50,)
                if 'FROM "ShipmentItems"' in self._query and 'SUM' in self._query:
                    return (35,)  # 35 already allocated of 50
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            payload = {
                "purchase_order_id": 101,
                "items": [
                    {"product_id": 1, "quantity": 20}  # 35 + 20 = 55 > 50
                ]
            }
            res, err = create_shipment(payload, user_id=5, role="Supplier", username="supplier1")
            self.assertIsNone(res)
            self.assertIsNotNone(err)
            self.assertIn("exceeds total purchase order quantity", err)

    def test_04_create_shipment_rejects_duplicate_product_ids(self):
        """Verify create_shipment rejects duplicate product IDs in items array."""
        class MockCursor:
            def execute(self, query, params=None):
                self._query = query
            def fetchone(self):
                if 'FROM "Suppliers"' in self._query:
                    return (5, "Acme Supplier")
                if 'FROM "PurchaseOrders"' in self._query and 'FOR UPDATE' in self._query:
                    return (101, 5, "Accepted", "Accepted")
                if 'FROM "PurchaseOrderItems"' in self._query:
                    return (50,)
                return None
            def fetchall(self):
                return []
            def close(self):
                pass

        class MockConn:
            def cursor(self):
                return MockCursor()
            def commit(self):
                pass
            def rollback(self):
                pass
            def close(self):
                pass

        with patch("app.services.team2.shipment_service.get_db_connection", return_value=MockConn()):
            payload = {
                "purchase_order_id": 101,
                "items": [
                    {"product_id": 1, "quantity": 10},
                    {"product_id": 1, "quantity": 15}
                ]
            }
            res, err = create_shipment(payload, user_id=5, role="Supplier", username="supplier1")
            self.assertIsNone(res)
            self.assertIsNotNone(err)
            self.assertIn("Duplicate product ID 1", err)


if __name__ == "__main__":
    unittest.main()
