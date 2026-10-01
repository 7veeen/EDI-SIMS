import unittest
import os
import sys
from unittest.mock import patch

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import create_app


class Team3DashboardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Login and obtain tokens for each role
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

    def test_01_owner_dashboard_success(self):
        """Test GET /api/dashboard/owner returns 200 and valid JSON for Owner role"""
        resp = self.client.get(
            "/api/dashboard/owner",
            headers={"Authorization": f"Bearer {self.owner_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        # Validate required response keys against actual dashboard service contract
        self.assertIn("total_users", data)
        self.assertIn("total_suppliers", data)
        self.assertIn("total_products", data)
        self.assertIn("total_inventory_value", data)
        self.assertIn("recent_audits", data)

        # Validate data types
        self.assertIsInstance(data["total_users"], int)
        self.assertIsInstance(data["total_suppliers"], int)
        self.assertIsInstance(data["total_products"], int)
        self.assertIsInstance(data["total_inventory_value"], (int, float))
        self.assertIsInstance(data["recent_audits"], list)

        # Validate inner item contract if audit records exist
        for audit in data["recent_audits"]:
            self.assertIn("log_id", audit)
            self.assertIn("action", audit)
            self.assertIn("username", audit)
            self.assertIn("timestamp", audit)
            self.assertIn("details", audit)

    def test_02_owner_dashboard_rbac_forbidden(self):
        """Test GET /api/dashboard/owner denies access with 403 to Manager, Employee, Supplier"""
        unauthorized_tokens = [
            ("Manager", self.manager_token),
            ("Employee", self.employee_token),
            ("Supplier", self.supplier_token),
        ]
        for role_name, token in unauthorized_tokens:
            with self.subTest(role=role_name):
                resp = self.client.get(
                    "/api/dashboard/owner",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp.status_code, 403)
                data = resp.get_json()
                self.assertEqual(data.get("error"), "Access denied")

    def test_03_manager_dashboard_success(self):
        """Test GET /api/dashboard/manager returns 200 and valid JSON for Manager role"""
        resp = self.client.get(
            "/api/dashboard/manager",
            headers={"Authorization": f"Bearer {self.manager_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        # Validate required response keys against actual dashboard service contract
        self.assertIn("active_pos", data)
        self.assertIn("pending_po_value", data)
        self.assertIn("low_stock_count", data)
        self.assertIn("recent_stock_movement", data)
        self.assertIn("recent_transactions", data)

        # Validate data types
        self.assertIsInstance(data["active_pos"], int)
        self.assertIsInstance(data["pending_po_value"], (int, float))
        self.assertIsInstance(data["low_stock_count"], int)
        self.assertIsInstance(data["recent_stock_movement"], int)
        self.assertIsInstance(data["recent_transactions"], list)

        # Validate inner item contract if transaction records exist
        for txn in data["recent_transactions"]:
            self.assertIn("transaction_id", txn)
            self.assertIn("product_name", txn)
            self.assertIn("transaction_type", txn)
            self.assertIn("quantity", txn)
            self.assertIn("transaction_date", txn)

    def test_04_manager_dashboard_rbac_forbidden(self):
        """Test GET /api/dashboard/manager denies access with 403 to Owner, Employee, Supplier"""
        unauthorized_tokens = [
            ("Owner", self.owner_token),
            ("Employee", self.employee_token),
            ("Supplier", self.supplier_token),
        ]
        for role_name, token in unauthorized_tokens:
            with self.subTest(role=role_name):
                resp = self.client.get(
                    "/api/dashboard/manager",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp.status_code, 403)
                data = resp.get_json()
                self.assertEqual(data.get("error"), "Access denied")

    def test_05_employee_dashboard_success(self):
        """Test GET /api/dashboard/employee returns 200 and valid JSON for Employee role"""
        resp = self.client.get(
            "/api/dashboard/employee",
            headers={"Authorization": f"Bearer {self.employee_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        # Validate required response keys against actual dashboard service contract
        self.assertIn("total_products", data)
        self.assertIn("total_stock", data)
        self.assertIn("stock_in", data)
        self.assertIn("stock_out", data)
        self.assertIn("low_stock_products", data)
        self.assertIn("tasks", data)

        # Validate data types
        self.assertIsInstance(data["total_products"], int)
        self.assertIsInstance(data["total_stock"], int)
        self.assertIsInstance(data["stock_in"], int)
        self.assertIsInstance(data["stock_out"], int)
        self.assertIsInstance(data["low_stock_products"], list)
        self.assertIsInstance(data["tasks"], list)

        # Validate inner item contract for low stock products if present
        for product in data["low_stock_products"]:
            self.assertIn("product_id", product)
            self.assertIn("product_name", product)
            self.assertIn("quantity_available", product)

        # Validate inner item contract for tasks if present
        for task in data["tasks"]:
            self.assertIn("notification_id", task)
            self.assertIn("title", task)
            self.assertIn("message", task)
            self.assertIn("created_at", task)
            self.assertIn("is_read", task)

    def test_06_employee_dashboard_rbac_forbidden(self):
        """Test GET /api/dashboard/employee denies access with 403 to Owner, Manager, Supplier"""
        unauthorized_tokens = [
            ("Owner", self.owner_token),
            ("Manager", self.manager_token),
            ("Supplier", self.supplier_token),
        ]
        for role_name, token in unauthorized_tokens:
            with self.subTest(role=role_name):
                resp = self.client.get(
                    "/api/dashboard/employee",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp.status_code, 403)
                data = resp.get_json()
                self.assertEqual(data.get("error"), "Access denied")

    def test_07_supplier_dashboard_success(self):
        """Test GET /api/dashboard/supplier returns 200 and valid JSON for Supplier role"""
        resp = self.client.get(
            "/api/dashboard/supplier",
            headers={"Authorization": f"Bearer {self.supplier_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)

        # Validate required response keys against actual dashboard service contract
        self.assertIn("total_purchase_orders", data)
        self.assertIn("received_orders", data)
        self.assertIn("completed_orders", data)
        self.assertIn("total_purchase_amount", data)
        self.assertIn("total_quotations", data)
        self.assertIn("pending_quotations", data)
        self.assertIn("approved_quotations", data)

        # Validate data types
        self.assertIsInstance(data["total_purchase_orders"], int)
        self.assertIsInstance(data["received_orders"], int)
        self.assertIsInstance(data["completed_orders"], int)
        self.assertIsInstance(data["total_purchase_amount"], (int, float))
        self.assertIsInstance(data["total_quotations"], int)
        self.assertIsInstance(data["pending_quotations"], int)
        self.assertIsInstance(data["approved_quotations"], int)

    def test_08_supplier_dashboard_rbac_forbidden(self):
        """Test GET /api/dashboard/supplier denies access with 403 to Owner, Manager, Employee"""
        unauthorized_tokens = [
            ("Owner", self.owner_token),
            ("Manager", self.manager_token),
            ("Employee", self.employee_token),
        ]
        for role_name, token in unauthorized_tokens:
            with self.subTest(role=role_name):
                resp = self.client.get(
                    "/api/dashboard/supplier",
                    headers={"Authorization": f"Bearer {token}"}
                )
                self.assertEqual(resp.status_code, 403)
                data = resp.get_json()
                self.assertEqual(data.get("error"), "Access denied")

    def test_09_unauthenticated_requests_return_401(self):
        """Test unauthenticated requests to all dashboard endpoints return 401 Unauthorized"""
        endpoints = [
            "/api/dashboard/owner",
            "/api/dashboard/manager",
            "/api/dashboard/employee",
            "/api/dashboard/supplier",
        ]
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint, scenario="missing_token"):
                resp = self.client.get(endpoint)
                self.assertEqual(resp.status_code, 401)

            with self.subTest(endpoint=endpoint, scenario="invalid_token"):
                resp = self.client.get(
                    endpoint,
                    headers={"Authorization": "Bearer invalid_malformed_token_xyz"}
                )
                self.assertIn(resp.status_code, [401, 422])

    def test_10_mocked_service_responses(self):
        """Test dashboard route serialization with predictable mocked service responses"""
        mock_owner_data = {
            "total_users": 10,
            "total_suppliers": 5,
            "total_products": 50,
            "total_inventory_value": 125000.0,
            "recent_audits": [
                {
                    "log_id": 1,
                    "action": "User Login",
                    "username": "demo_owner",
                    "timestamp": "2026-09-26T12:00:00",
                    "details": "User logged in from 127.0.0.1"
                }
            ]
        }
        with patch("app.routes.team3.dashboard.get_owner_dashboard", return_value=mock_owner_data):
            resp = self.client.get(
                "/api/dashboard/owner",
                headers={"Authorization": f"Bearer {self.owner_token}"}
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json(), mock_owner_data)

        mock_manager_data = {
            "active_pos": 3,
            "pending_po_value": 4500.0,
            "low_stock_count": 2,
            "recent_stock_movement": 150,
            "recent_transactions": [
                {
                    "transaction_id": 101,
                    "product_name": "Test Item",
                    "transaction_type": "STOCK_IN",
                    "quantity": 25,
                    "transaction_date": "2026-09-26T12:30:00"
                }
            ]
        }
        with patch("app.routes.team3.dashboard.get_manager_dashboard", return_value=mock_manager_data):
            resp = self.client.get(
                "/api/dashboard/manager",
                headers={"Authorization": f"Bearer {self.manager_token}"}
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json(), mock_manager_data)


if __name__ == "__main__":
    unittest.main()
