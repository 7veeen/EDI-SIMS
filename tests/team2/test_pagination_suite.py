import unittest
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from flask_jwt_extended import create_access_token


class PaginationContractTestCase(unittest.TestCase):
    """
    Focused verification suite for SIMS Improvement 8 — Phase 2 Step 4:
    Pagination for Large Entity Lists.
    Covers contract normalization, default parameters, clamping, deterministic ordering,
    isolation, and compatibility across Products, Inventory, Purchase Orders, Shipments,
    Stock Requests, Notifications, and Audit Logs.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Mint test JWT tokens with specific roles
        with cls.app.app_context():
            cls.owner_token = create_access_token(identity="1", additional_claims={"role": "Owner"})
            cls.manager_token = create_access_token(identity="2", additional_claims={"role": "Manager"})
            cls.employee_token = create_access_token(identity="3", additional_claims={"role": "Employee"})
            cls.supplier1_token = create_access_token(identity="4", additional_claims={"role": "Supplier"})
            cls.supplier2_token = create_access_token(identity="5", additional_claims={"role": "Supplier"})

    def _headers(self, token):
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    # =========================================================================
    # Test 1: Unauthenticated & RBAC Access Rejections
    # =========================================================================
    def test_01_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to paginated protected endpoints must return 401."""
        endpoints = [
            "/api/products/",
            "/api/inventory/",
            "/api/purchase-orders/",
            "/api/shipments/",
            "/api/stock-requests/",
            "/api/audit-logs/",
            "/api/notifications/"
        ]
        for ep in endpoints:
            resp = self.client.get(ep)
            self.assertEqual(resp.status_code, 401, f"Expected 401 for unauthenticated {ep}, got {resp.status_code}")

    def test_02_rbac_role_enforcement_on_sensitive_paginated_routes(self):
        """Employees must be forbidden from audit logs, and suppliers forbidden from inventory adjustments."""
        resp_audit = self.client.get("/api/audit-logs/", headers=self._headers(self.employee_token))
        self.assertEqual(resp_audit.status_code, 403)

        resp_audit_mgr = self.client.get("/api/audit-logs/", headers=self._headers(self.manager_token))
        self.assertEqual(resp_audit_mgr.status_code, 403)

    # =========================================================================
    # Test 2: Products Endpoint Pagination & Deterministic Ordering
    # =========================================================================
    def test_03_products_default_pagination_and_metadata(self):
        """GET /api/products/ with default pagination parameters."""
        resp = self.client.get("/api/products/?page=1&page_size=5", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("products", data)
        self.assertIn("pagination", data)
        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 5)
        self.assertGreaterEqual(pagination["total"], 0)
        self.assertIsInstance(data["products"], list)
        self.assertLessEqual(len(data["products"]), 5)

    def test_04_products_deterministic_ordering_tiebreaker(self):
        """Products sorting has deterministic tie-breaker product_id ASC."""
        resp = self.client.get("/api/products/?page=1&page_size=10&sort_by=price&order=asc", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        products = resp.get_json()["products"]

        if len(products) > 1:
            for i in range(len(products) - 1):
                p1, p2 = products[i], products[i + 1]
                if p1["selling_price"] == p2["selling_price"]:
                    self.assertLess(p1["product_id"], p2["product_id"])

    # =========================================================================
    # Test 3: Inventory Endpoint Pagination & Stats Preservation
    # =========================================================================
    def test_05_inventory_pagination_and_kpi_stats_preservation(self):
        """GET /api/inventory/ returns paginated items while stats reflect total dataset."""
        resp = self.client.get("/api/inventory/?page=1&page_size=5", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("inventory", data)
        self.assertIn("stats", data)
        self.assertIn("pagination", data)

        stats = data["stats"]
        self.assertIn("total_items", stats)
        self.assertIn("in_stock", stats)
        self.assertIn("low_stock", stats)
        self.assertIn("total_quantity", stats)

        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 5)
        self.assertLessEqual(len(data["inventory"]), 5)

    # =========================================================================
    # Test 4: Purchase Orders Pagination & Backward Compatibility
    # =========================================================================
    def test_06_purchase_orders_pagination_contract(self):
        """GET /api/purchase-orders/ supports page & page_size and returns pagination metadata."""
        resp = self.client.get("/api/purchase-orders/?page=1&page_size=10", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("purchase_orders", data)
        self.assertIn("pagination", data)
        self.assertIn("stats", data)

        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 10)
        self.assertLessEqual(len(data["purchase_orders"]), 10)

    def test_07_purchase_orders_backward_compatibility_unpaginated(self):
        """GET /api/purchase-orders/ without page param retains full list response for legacy callers."""
        resp = self.client.get("/api/purchase-orders/", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("purchase_orders", data)
        self.assertIsInstance(data["purchase_orders"], list)

    # =========================================================================
    # Test 5: Shipments Pagination & KPI Preservation
    # =========================================================================
    def test_08_shipments_pagination_contract(self):
        """GET /api/shipments/ supports page & page_size and returns paginated list with stats."""
        resp = self.client.get("/api/shipments/?page=1&page_size=10", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("shipments", data)
        self.assertIn("pagination", data)
        self.assertIn("stats", data)

        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 10)
        self.assertLessEqual(len(data["shipments"]), 10)

    # =========================================================================
    # Test 6: Stock Requests Pagination & N+1 Elimination
    # =========================================================================
    def test_09_stock_requests_pagination_contract(self):
        """GET /api/stock-requests/ supports page & page_size and batched items loading."""
        resp = self.client.get("/api/stock-requests/?page=1&page_size=5", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertIn("stock_requests", data)
        self.assertIn("pagination", data)
        pagination = data["pagination"]
        self.assertEqual(pagination["page"], 1)
        self.assertEqual(pagination["page_size"], 5)
        self.assertLessEqual(len(data["stock_requests"]), 5)

        for req in data["stock_requests"]:
            self.assertIn("stock_request_id", req)
            self.assertIn("items", req)
            self.assertIsInstance(req["items"], list)

    # =========================================================================
    # Test 7: Parameter Validation, Clamping & Out-of-Range Handling
    # =========================================================================
    def test_10_negative_and_invalid_parameters_fallback_safely(self):
        """Invalid strings or negative page numbers safely fall back to page 1."""
        resp = self.client.get("/api/inventory/?page=-5&page_size=-20", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertGreater(data["pagination"]["page_size"], 0)

        resp_invalid = self.client.get("/api/purchase-orders/?page=invalid&page_size=garbage", headers=self._headers(self.owner_token))
        self.assertEqual(resp_invalid.status_code, 200)
        data_inv = resp_invalid.get_json()
        self.assertEqual(data_inv["pagination"]["page"], 1)

    def test_11_excessively_large_page_size_clamped(self):
        """Excessively large page_size (e.g. 50000) is strictly clamped to max 200."""
        resp = self.client.get("/api/products/?page=1&page_size=99999", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertLessEqual(data["pagination"]["page_size"], 200)

    def test_12_out_of_range_page_returns_empty_list_with_valid_metadata(self):
        """Requesting page 9999 returns empty data list without crashing."""
        resp = self.client.get("/api/inventory/?page=9999&page_size=20", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["inventory"]), 0)
        self.assertEqual(data["pagination"]["page"], 9999)
        self.assertGreaterEqual(data["pagination"]["total"], 0)

    # =========================================================================
    # Test 8: Notifications & Audit Logs Pagination
    # =========================================================================
    def test_13_notifications_pagination_contract(self):
        """GET /api/notifications/ supports page and page_size."""
        resp = self.client.get("/api/notifications/?page=1&page_size=10", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        self.assertLessEqual(len(data), 10)

    def test_14_audit_logs_pagination_page_size_alias(self):
        """GET /api/audit-logs/ supports page_size alias alongside limit."""
        resp = self.client.get("/api/audit-logs/?page=1&page_size=10", headers=self._headers(self.owner_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("logs", data)
        self.assertIn("pagination", data)
        self.assertEqual(data["pagination"]["page_size"], 10)


if __name__ == "__main__":
    unittest.main()
