import unittest
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app
from app.services.team2.stock_request_service import (
    get_stock_requests,
    get_stock_request_by_id,
    respond_to_stock_request
)


class StockRequestRouteAuthorizationTestCase(unittest.TestCase):
    """
    Test suite for SIMS Improvement 2: Stock Request Route Authorization.
    Verifies explicit route-level RBAC enforcement, supplier isolation,
    service-level defense-in-depth, and regression safety.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role using existing test accounts
        cls.owner_token = cls._get_token("demo_owner", "password123")
        cls.manager_token = cls._get_token("demo_manager", "password123")
        cls.employee_token = cls._get_token("demo_employee", "password123")
        cls.supplier_token = cls._get_token("demo_supplier", "password123")

        # Sanity check tokens
        assert cls.owner_token, "Failed to obtain owner token"
        assert cls.manager_token, "Failed to obtain manager token"
        assert cls.employee_token, "Failed to obtain employee token"
        assert cls.supplier_token, "Failed to obtain supplier token"

    @classmethod
    def _get_token(cls, username, password):
        resp = cls.client.post("/api/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.get_json() or {}
        return data.get("access_token")

    # =========================================================================
    # Group 1: Authentication & Invalid Tokens
    # =========================================================================

    def test_01_unauthenticated_list_requests_rejected(self):
        """Unauthenticated requests to GET /api/stock-requests/ must return 401."""
        resp = self.client.get("/api/stock-requests/")
        self.assertEqual(resp.status_code, 401)

    def test_02_unauthenticated_single_request_rejected(self):
        """Unauthenticated requests to GET /api/stock-requests/<id> must return 401."""
        resp = self.client.get("/api/stock-requests/1")
        self.assertEqual(resp.status_code, 401)

    def test_03_unauthenticated_create_request_rejected(self):
        """Unauthenticated requests to POST /api/stock-requests/ must return 401."""
        resp = self.client.post("/api/stock-requests/", json={"supplier_id": 1, "items": []})
        self.assertEqual(resp.status_code, 401)

    def test_04_unauthenticated_respond_request_rejected(self):
        """Unauthenticated requests to PATCH/POST /api/stock-requests/<id>/respond must return 401."""
        resp = self.client.patch("/api/stock-requests/1/respond", json={"action": "Accept"})
        self.assertEqual(resp.status_code, 401)

    def test_05_invalid_token_rejected(self):
        """Requests with an invalid Bearer token must return 422 or 401."""
        resp = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": "Bearer invalid_garbage_token_12345"}
        )
        self.assertIn(resp.status_code, [401, 422])

    # =========================================================================
    # Group 2: Route-Level RBAC Enforcement for Employee (Audit Finding)
    # =========================================================================

    def test_06_employee_cannot_list_stock_requests_route_rbac(self):
        """
        REGRESSION TEST FOR AUDIT FINDING:
        Employee accessing GET /api/stock-requests/ must be rejected at route-level
        with HTTP 403 Forbidden.
        """
        resp = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json() or {}
        self.assertIn("error", data)
        self.assertEqual(data.get("error"), "Access denied")
        self.assertEqual(data.get("message"), "You do not have permission to perform this action")

    def test_07_employee_cannot_access_single_stock_request_route_rbac(self):
        """
        Employee accessing GET /api/stock-requests/<id> must be rejected at route-level
        with HTTP 403 Forbidden.
        """
        resp = self.client.get(
            "/api/stock-requests/1",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json() or {}
        self.assertEqual(data.get("error"), "Access denied")
        self.assertEqual(data.get("message"), "You do not have permission to perform this action")

    def test_08_employee_cannot_create_stock_request(self):
        """
        Employee attempting to POST /api/stock-requests/ must be rejected with HTTP 403.
        """
        resp = self.client.post(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.employee_token}"},
            json={"supplier_id": 5, "items": [{"product_id": 1, "requested_quantity": 5}]}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json() or {}
        self.assertEqual(data.get("error"), "Access denied")

    def test_09_employee_cannot_respond_to_stock_request(self):
        """
        Employee attempting to respond to a stock request must be rejected with HTTP 403.
        """
        resp = self.client.patch(
            "/api/stock-requests/1/respond",
            headers={"Authorization": f"Bearer {self.employee_token}"},
            json={"action": "Accept"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json() or {}
        self.assertEqual(data.get("error"), "Access denied")

    # =========================================================================
    # Group 3: Owner & Manager Authorized Access
    # =========================================================================

    def test_10_owner_can_list_stock_requests(self):
        """Owner can successfully list organization stock requests."""
        resp = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_requests", data)
        self.assertIsInstance(data["stock_requests"], list)

    def test_11_manager_can_list_stock_requests(self):
        """Manager can successfully list organization stock requests."""
        resp = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_requests", data)
        self.assertIsInstance(data["stock_requests"], list)

    def test_12_owner_can_view_single_stock_request(self):
        """Owner can view detailed single stock request."""
        resp = self.client.get(
            "/api/stock-requests/1",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_request", data)
        self.assertEqual(data["stock_request"]["stock_request_id"], 1)

    def test_13_manager_can_view_single_stock_request(self):
        """Manager can view detailed single stock request."""
        resp = self.client.get(
            "/api/stock-requests/1",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_request", data)
        self.assertEqual(data["stock_request"]["stock_request_id"], 1)

    def test_14_bare_url_alias_works_for_authorized_users(self):
        """Both /api/stock-requests/ and /api/stock-requests work for authorized roles."""
        resp_slash = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        resp_bare = self.client.get(
            "/api/stock-requests",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp_slash.status_code, 200)
        self.assertEqual(resp_bare.status_code, 200)
        self.assertEqual(len(resp_slash.get_json()["stock_requests"]), len(resp_bare.get_json()["stock_requests"]))

    # =========================================================================
    # Group 4: Supplier Authorized Access & Supplier Isolation
    # =========================================================================

    def test_15_supplier_can_list_own_stock_requests(self):
        """Supplier can list stock requests assigned to their supplier profile."""
        resp = self.client.get(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_requests", data)
        # All requests returned must belong to demo_supplier (supplier_id = 5)
        for req in data["stock_requests"]:
            self.assertEqual(
                req.get("supplier_id"), 5,
                f"Supplier isolation breach: supplier saw request belonging to supplier {req.get('supplier_id')}"
            )

    def test_16_supplier_cannot_bypass_isolation_via_query_param(self):
        """
        Supplier attempting to query another supplier's requests via ?supplier_id=4
        must still only receive requests belonging to their own supplier (supplier_id = 5).
        """
        resp = self.client.get(
            "/api/stock-requests/?supplier_id=4",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_requests", data)
        for req in data["stock_requests"]:
            self.assertEqual(
                req.get("supplier_id"), 5,
                "Query parameter manipulation allowed supplier to view foreign supplier data"
            )

    def test_17_supplier_can_view_own_stock_request_detail(self):
        """Supplier can view details of stock request 1 (assigned to supplier 5)."""
        resp = self.client.get(
            "/api/stock-requests/1",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("stock_request", data)
        self.assertEqual(data["stock_request"]["supplier_id"], 5)

    def test_18_supplier_cannot_view_another_suppliers_stock_request(self):
        """
        Supplier attempting to view request 2 (assigned to supplier 4)
        must receive HTTP 403 Forbidden.
        """
        resp = self.client.get(
            "/api/stock-requests/2",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("error", data)
        self.assertIn("Access denied", data["error"])

    def test_19_supplier_cannot_create_stock_request(self):
        """Supplier attempting to POST /api/stock-requests/ is rejected with HTTP 403."""
        resp = self.client.post(
            "/api/stock-requests/",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"supplier_id": 5, "items": [{"product_id": 1, "requested_quantity": 5}]}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json() or {}
        self.assertEqual(data.get("error"), "Access denied")

    def test_20_supplier_cannot_respond_to_foreign_stock_request(self):
        """Supplier cannot respond to request 2 (assigned to supplier 4)."""
        resp = self.client.patch(
            "/api/stock-requests/2/respond",
            headers={"Authorization": f"Bearer {self.supplier_token}"},
            json={"action": "Accept"}
        )
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertIn("error", data)
        self.assertIn("Access denied", data["error"])

    # =========================================================================
    # Group 5: Service-Level Defense-in-Depth Direct Calls
    # =========================================================================

    def test_21_service_level_employee_rejection_list(self):
        """Direct service call to get_stock_requests with role='Employee' returns access denied."""
        results, err = get_stock_requests(user_id=7, role="Employee")
        self.assertIsNone(results)
        self.assertIn("Access denied", err)

    def test_22_service_level_employee_rejection_detail(self):
        """Direct service call to get_stock_request_by_id with role='Employee' returns access denied."""
        result, err = get_stock_request_by_id(stock_request_id=1, user_id=7, role="Employee")
        self.assertIsNone(result)
        self.assertIn("Access denied", err)

    def test_23_service_level_supplier_isolation_detail(self):
        """Direct service call with user_id=8 (supplier 5) querying request 2 (supplier 4) returns access denied."""
        result, err = get_stock_request_by_id(stock_request_id=2, user_id=8, role="Supplier")
        self.assertIsNone(result)
        self.assertIn("Access denied", err)

    def test_24_service_level_supplier_isolation_respond(self):
        """Direct service call to respond_to_stock_request for foreign request returns access denied."""
        result, err = respond_to_stock_request(
            stock_request_id=2,
            user_id=8,
            role="Supplier",
            data={"action": "Accept"}
        )
        self.assertIsNone(result)
        self.assertIn("Access denied", err)


if __name__ == "__main__":
    unittest.main()
